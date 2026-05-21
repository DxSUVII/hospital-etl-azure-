"""
Phase 5 — Lambda function for daily hospital report
Triggered by CloudWatch Events on a schedule.
Queries RDS → builds CSV report → saves to S3 reports/ folder

DEPENDENCIES:
- Uses AWSSDKPandas-Python311 layer (ARN: ...336392948345:layer:AWSSDKPandas-Python311:31)
- This layer provides pandas, boto3, sqlalchemy, and psycopg2-binary automatically.
"""
import boto3
import pandas as pd
import os
import io
from datetime import datetime
from sqlalchemy import create_engine

def get_db_engine():
    """
    Creates a SQLAlchemy engine for RDS PostgreSQL using environment variables.
    
    NOTE: We use 'postgresql+psycopg2' explicitly to ensure SQLAlchemy uses 
    the psycopg2 driver bundled in the AWS layer, avoiding fallback issues.
    """
    host     = os.environ.get("RDS_HOST")
    port     = os.environ.get("RDS_PORT", "5432")
    database = os.environ.get("RDS_DATABASE", "postgres")
    user     = os.environ.get("RDS_USER")
    password = os.environ.get("RDS_PASSWORD")
    
    # Construct connection string
    # Using postgresql+psycopg2 ensures we use the binary driver from the layer
    connection_uri = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
    
    return create_engine(connection_uri)

def run_query(engine, sql):
    """
    Runs a SQL query and returns results as a pandas DataFrame.
    Uses context manager to ensure connections are closed properly.
    """
    try:
        with engine.connect() as conn:
            return pd.read_sql_query(sql, conn)
    except Exception as e:
        print(f"Error running query: {e}")
        raise

def upload_to_s3(content_bytes, s3_key):
    """Uploads bytes to S3. Used to save the report CSV."""
    s3 = boto3.client("s3")
    bucket = os.environ.get("S3_BUCKET")
    
    if not bucket:
        raise ValueError("S3_BUCKET environment variable is not set")
        
    s3.put_object(
        Bucket=bucket, 
        Key=s3_key, 
        Body=content_bytes,
        ContentType="text/csv"
    )
    print(f"  Saved to s3://{bucket}/{s3_key}")

def lambda_handler(event, context):
    """
    Lambda entry point — AWS calls this function when triggered.
    """
    today  = datetime.now().strftime("%Y-%m-%d")
    report = {}

    print(f"Daily hospital report — {today}")

    try:
        # Initialize the database engine
        engine = get_db_engine()
        print("  Database engine initialized")

        # Define all 6 analytical queries
        queries = {
            "visits_by_branch": """
                SELECT branch_id,
                       TO_CHAR(date_of_consultation,'YYYY-MM') AS month,
                       COUNT(*) AS visit_count
                FROM appointments
                GROUP BY branch_id, TO_CHAR(date_of_consultation,'YYYY-MM')
                ORDER BY month, visit_count DESC
            """,
            "revenue_by_branch": """
                SELECT branch_id,
                       COUNT(*) AS total_claims,
                       ROUND(SUM(total_bill)::NUMERIC,2) AS total_revenue,
                       ROUND(AVG(total_bill)::NUMERIC,2) AS avg_bill
                FROM billing 
                GROUP BY branch_id
                ORDER BY total_revenue DESC
            """,
            "top_diagnoses": """
                SELECT diagnosis, COUNT(*) AS frequency
                FROM appointments
                GROUP BY diagnosis 
                ORDER BY frequency DESC 
                LIMIT 10
            """,
            "surgery_outcomes": """
                SELECT doctor_id, COUNT(*) AS total_surgeries,
                       SUM(CASE WHEN surgery_outcome='Successful' THEN 1 ELSE 0 END) AS successful,
                       SUM(CASE WHEN surgery_outcome='Failed' THEN 1 ELSE 0 END) AS failed
                FROM surgeries
                GROUP BY doctor_id 
                ORDER BY total_surgeries DESC 
                LIMIT 20
            """,
            "claim_status": """
                SELECT insurance_provider, COUNT(*) AS total_claims,
                       SUM(CASE WHEN claim_status='Approved' THEN 1 ELSE 0 END) AS approved,
                       SUM(CASE WHEN claim_status='Rejected' THEN 1 ELSE 0 END) AS rejected,
                       SUM(CASE WHEN claim_status='Pending'  THEN 1 ELSE 0 END) AS pending
                FROM billing
                GROUP BY insurance_provider 
                ORDER BY total_claims DESC
            """,
            "doctor_substitution": """
                SELECT branch_id, COUNT(*) AS total_appointments,
                       SUM(CASE WHEN requested_doctor_id != consulted_doctor_id THEN 1 ELSE 0 END) AS substitutions
                FROM appointments
                GROUP BY branch_id 
                ORDER BY substitutions DESC
            """
        }

        # Execute queries and store results
        for name, sql in queries.items():
            print(f"  Running query: {name}...")
            df = run_query(engine, sql)
            report[name] = df
            print(f"    → {len(df)} rows returned")

        # Build the CSV report in memory
        output = io.StringIO()
        
        for name, df in report.items():
            # Add a header row to separate sections in the CSV
            output.write(f"\n### {name.upper()} ###\n")
            # Write DataFrame to CSV (index=False skips pandas row numbers)
            df.to_csv(output, index=False)
        
        # Convert text buffer to bytes for S3 upload
        csv_bytes = output.getvalue().encode("utf-8")
        
        # Save to S3
        s3_key = f"reports/daily_report_{today}.csv"
        upload_to_s3(csv_bytes, s3_key)
        
        print(" Report generation complete")

        return {
            "statusCode": 200,
            "body": f"Report saved to {s3_key}"
        }

    except Exception as e:
        print(f" Error during execution: {str(e)}")
        return {
            "statusCode": 500,
            "body": f"Internal Server Error: {str(e)}"
        }