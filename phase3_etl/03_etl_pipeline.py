"""
Phase 3 — ETL Pipeline
Read CSVs from S3 → transform in pandas → load into RDS PostgreSQL

WHY pandas instead of Glue?
Glue Spark jobs cost $0.88 minimum per run — not free tier friendly.
For 5.4MB of data, pandas completes the same job in under 10 seconds
at zero cost. Glue is the production-scale choice for TB-scale data.
We document this decision in the architecture doc.
"""

import boto3
import pandas as pd
import psycopg2
import ast
import os
import io
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv() 

# Configuration
S3_BUCKET = os.getenv("S3_BUCKET_NAME")
S3_PREFIX = "raw/"
RDS_HOST = os.getenv("RDS_HOST")
RDS_PORT = os.getenv("RDS_PORT")
RDS_DB = os.getenv("RDS_DB_NAME")
RDS_USER = os.getenv("RDS_USER")
RDS_PASS = os.getenv("RDS_PASSWORD")

#-----HELPERS-----

def get_s3_client():
    """ Creates an S3 client using credentials from environment variables """
    return boto3.client("s3", region_name=os.getenv("AWS_REGION", 'ap-south-1'))

def get_db_engine():
    """
    SQLAlchemy engine — creates a connection pool to RDS PostgreSQL.
    Connection string format for PostgreSQL:
    postgresql://user:password@host:port/database
    """ 
    port_env = os.getenv("RDS_PORT")
    port = int(port_env) if port_env and port_env != 'None' else 5432
    conn_str = f"postgresql://{RDS_USER}:{RDS_PASS}@{RDS_HOST}:{port}/{RDS_DB}"
    return create_engine(conn_str)    

def read_csv_from_s3(s3_client, filename):
    key = f"{S3_PREFIX}{filename}"
    print(f"  Reading s3://{S3_BUCKET}/{key}")
    response = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
    content = response["Body"].read()
    df = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")
    print(f"  Loaded: {len(df):,} rows × {len(df.columns)} columns")
    return df

def run_sql_file(engine, filename):
    """Runs a .sql file — used to execute 03_create_tables.sql"""
    filepath = os.path.join(os.path.dirname(__file__), filename)
    with open(filepath, "r") as f:
        sql = f.read()
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
    print("  Tables created successfully")

def clean_header_format(df):
    """
    Standardizes raw column names by converting spaces, dots, hyphens, and brackets 
    into clean underscores, eliminating case-mismatch lookup bugs.
    """
    df.columns = df.columns.str.replace(r'[.\s()\-]+', '_', regex=True).str.strip('_')
    return df

def cast_yes_no(df, columns):
    for col in columns:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.lower().isin(["yes", "true", "1"])
    return df

def cast_dates(df, columns):
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=False, errors="coerce")
    return df

def rename_columns(df, rename_map):
    return df.rename(columns=rename_map)

def load_to_rds(df, table_name, engine):
    try:
        df.to_sql(table_name, engine, if_exists="append",
                  index=False, method="multi")
        print(f"  Loaded {len(df):,} rows -> {table_name}")
    except Exception as e:
        print(f"\n ERROR loading {table_name}:")
        print(f"{type(e).__name__}: {str(e)}\n")
        raise

# ------  Transform functions per table
def transform_branches(df):
    df = clean_header_format(df)
    df = rename_columns(df, {
        "Sl_No": "serial_no", "Serial_No": "serial_no", "Branch_ID": "branch_id",
        "Location": "location", "OT_Available": "ot_available",
        "Inhouse_Anesthetician": "inhouse_anesthetician",
        "No_of_OTs": "no_of_ots", "Inhouse_Pharmacy": "inhouse_pharmacy",
        "Inhouse_Nutritionist": "inhouse_nutritionist",
        "Inpatient_Rooms": "inpatient_rooms",
        "Luxury_Suite_Rooms": "luxury_suite_rooms",
        "Prayer_Room": "prayer_room", "Kids_Play_Area": "kids_play_area"
    })
    yes_no_cols = ["ot_available", "inhouse_anesthetician", "inhouse_pharmacy",
                   "inhouse_nutritionist", "luxury_suite_rooms",
                   "prayer_room", "kids_play_area"]
    df = cast_yes_no(df, yes_no_cols)
    
    # Deduplicate primary key to prevent UniqueViolation error
    df = df.drop_duplicates(subset=["branch_id"], keep="first")
    return df

def transform_doctors(df):
    # Extract doctor_branch_visits BEFORE header standardization to safely find raw column name
    branch_rows = []
    for _, row in df.iterrows():
        try:
            if pd.notna(row["Other Branches Visited"]):
                branches = ast.literal_eval(row["Other Branches Visited"])
                for b in branches:
                    branch_rows.append({"doctor_id": row["Doctor ID"],
                                        "branch_id": b.strip()})
        except (ValueError, SyntaxError):
            pass
    branch_df = pd.DataFrame(branch_rows)
    if not branch_df.empty:
        branch_df = branch_df.drop_duplicates(subset=["doctor_id", "branch_id"])

    # Standardize and clean doctors master structure
    df = clean_header_format(df)
    df = rename_columns(df, {
        "Sl_No": "serial_no", "Serial_No": "serial_no", "Doctor_Name": "doctor_name",
        "Doctor_ID": "doctor_id", "Specialization": "specialization",
        "Qualification": "qualification",
        "Surgery_Experience": "surgery_experience",
        "Practicing_Branch": "practicing_branch"
    })
    df = df.drop(columns=["Other_Branches_Visited"], errors="ignore")
    
    # Deduplicate primary key
    df = df.drop_duplicates(subset=["doctor_id"], keep="first")
    return df, branch_df

def transform_patients(df):
    df = clean_header_format(df)
    df = rename_columns(df, {
        "Sl_No": "serial_no", "Serial_No": "serial_no", "Patient_ID": "patient_id",
        "Date_of_Registration": "date_of_registration",
        "Date_of_First_Consultation": "date_of_first_consultation",
        "Date_of_Latest_Consultation": "date_of_latest_consultation",
        "Overall_Satisfaction_Rating": "overall_satisfaction_rating",
        "Admission": "admission", "Surgery_Underwent": "surgery_underwent",
        "Total_Number_of_Visits": "total_number_of_visits"
    })
    df = cast_yes_no(df, ["admission", "surgery_underwent"])
    df = cast_dates(df, ["date_of_registration", "date_of_first_consultation", "date_of_latest_consultation"])
    
    # Deduplicate primary key
    df = df.drop_duplicates(subset=["patient_id"], keep="first")
    return df

def transform_appointments(df):
    df = clean_header_format(df)
    df = rename_columns(df, {
        "Sl_No": "serial_no", "Serial_No": "serial_no", "Case_ID": "case_id",
        "Patient_ID": "patient_id", "Branch_ID": "branch_id",
        "Date_of_Consultation": "date_of_consultation",
        "Requested_Doctor_ID": "requested_doctor_id",
        "Consulted_Doctor_ID": "consulted_doctor_id",
        "Reason_for_Visit": "reason_for_visit", "Diagnosis": "diagnosis",
        "Prescribed_Medication": "prescribed_medication",
        "Followup_Required": "followup_required",
        "Nutritionist_Recommended": "nutritionist_recommended"
    })
    df = cast_yes_no(df, ["followup_required", "nutritionist_recommended"])
    df = cast_dates(df, ["date_of_consultation"])
    return df

def transform_billing(df):
    df = clean_header_format(df)
    df = rename_columns(df, {
        "Sl_No": "serial_no", "Serial_No": "serial_no", "Claim_ID": "claim_id",
        "Patient_ID": "patient_id", "Case_ID": "case_id",
        "Branch_ID": "branch_id", "Total_Bill": "total_bill",
        "Insurance_Provider": "insurance_provider",
        "Amount_Covered": "amount_covered",
        "Out_of_Pocket_Expenses": "out_of_pocket_expenses",
        "Claim_Status": "claim_status"
    })
    df["claim_id"] = pd.to_numeric(df["claim_id"], errors="coerce").fillna(0).astype("int64")
    df["case_id"]  = pd.to_numeric(df["case_id"], errors="coerce").fillna(0).astype("int64")
    return df

def transform_surgeries(df):
    df = clean_header_format(df)
    df = rename_columns(df, {
        "Sl_No": "serial_no", "Serial_No": "serial_no", "Case_ID": "case_id",
        "Patient_ID": "patient_id", "Doctor_ID": "doctor_id",
        "Branch_ID": "branch_id", "Surgery_Type": "surgery_type",
        "Surgery_Date": "surgery_date", "Anesthesia_Type": "anesthesia_type",
        "Surgery_Outcome": "surgery_outcome",
        "Surgery_Duration_hours": "surgery_duration_hours",
        "Recovery_Period_days": "recovery_period_days"
    })
    return cast_dates(df, ["surgery_date"])

def transform_lab_reports(df):
    df = clean_header_format(df)
    df = rename_columns(df, {
        "Sl_No": "serial_no", "Serial_No": "serial_no", "Report_ID": "report_id",
        "Case_ID": "case_id", "Patient_ID": "patient_id",
        "Branch_ID": "branch_id", "Test_Name": "test_name",
        "Test_Date": "test_date", "Result": "result"
    })
    df["case_id"] = pd.to_numeric(df["case_id"], errors="coerce").fillna(0).astype("int64")
    return cast_dates(df, ["test_date"])

def transform_prescriptions(df):
    df = clean_header_format(df)
    df = rename_columns(df, {
        "Sl_No": "serial_no", "Serial_No": "serial_no", "Bill_ID": "bill_id",
        "Patient_ID": "patient_id", "Doctor_ID": "doctor_id",
        "Medication_Name": "medication_name", "Dosage": "dosage",
        "Quantity": "quantity",
        "Pharmacy_Availability": "pharmacy_availability",
        "Issued_Date": "issued_date"
    })
    df = cast_yes_no(df, ["pharmacy_availability"])
    return cast_dates(df, ["issued_date"])
    
#---Main ETL orchestration -------
def main():
    print("=" * 55)
    print(" PHASE 3 — ETL PIPELINE")
    print("=" * 55)

    s3 = get_s3_client()
    engine = get_db_engine()

    # Step 1: Create tables
    print("\n[Step 1] Creating tables in RDS...")
    run_sql_file(engine, "03_create_tables.sql")

    # Step 2: Load dimension tables FIRST (no FK dependencies)
    print("\n[Step 2] Loading dimension tables...")

    df = read_csv_from_s3(s3, "branches.csv")
    load_to_rds(transform_branches(df), "branches", engine)

    df = read_csv_from_s3(s3, "doctors.csv")
    doctors_df, branch_visits_df = transform_doctors(df)
    load_to_rds(doctors_df, "doctors", engine)
    
    if not branch_visits_df.empty:
        load_to_rds(branch_visits_df, "doctor_branch_visits", engine)

    df = read_csv_from_s3(s3, "patients.csv")
    load_to_rds(transform_patients(df), "patients", engine)

    # Step 3: Load fact tables SECOND (reference dimensions)
    print("\n[Step 3] Loading fact tables...")

    df = read_csv_from_s3(s3, "appointments.csv")
    load_to_rds(transform_appointments(df), "appointments", engine)

    df = read_csv_from_s3(s3, "billing.csv")
    load_to_rds(transform_billing(df), "billing", engine)

    df = read_csv_from_s3(s3, "surgeries.csv")
    load_to_rds(transform_surgeries(df), "surgeries", engine)

    df = read_csv_from_s3(s3, "lab_reports.csv")
    load_to_rds(transform_lab_reports(df), "lab_reports", engine)

    df = read_csv_from_s3(s3, "prescriptions.csv")
    load_to_rds(transform_prescriptions(df), "prescriptions", engine)

    # Step 4: Verify row counts
    print("\n[Step 4] Verifying row counts in RDS...")
    tables = ["branches", "doctors", "doctor_branch_visits", "patients",
              "appointments", "billing", "surgeries", "lab_reports", "prescriptions"]
    with engine.connect() as conn:
        for table in tables:
            try:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"  {table:<30} {count:>7,} rows")
            except Exception as e:
                print(f"  Could not count table {table}: {e}")

    print("\n ETL complete. Screenshot the row counts above.")
    print(" Then go to RDS Query Editor and screenshot the tables.")

if __name__ == "__main__":
    main()