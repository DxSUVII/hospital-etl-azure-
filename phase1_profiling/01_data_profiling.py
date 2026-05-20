import pandas as pd
import ast      # Used to safely turn string lists like "['A', 'B']" into real Python lists
import os       # Used to handle file paths and check if files exist
from datetime import datetime 

# --- CONFIGURATION ---
# ".." means go up one folder from where this script is running.
# This script is in phase1_profiling/, so we go up to hospital-etl-azure/ then into data/raw/
CSV_FOLDER = "../data/raw"

# A dictionary mapping a simple name to the actual filename.
FILES = {
    "appointments": "appointments.csv",
    "billing": "billing.csv",
    "patients": "patients.csv",
    "doctors": "doctors.csv",
    "surgeries": "surgeries.csv",
    "prescriptions": "prescriptions.csv",
    "lab_reports": "lab_reports.csv",
    "branches": "branches.csv",
}

# --- HELPER FUNCTIONS ---

def print_header(title):
    """
    Prints a big header with equals signs to separate major steps in the output.
    """
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)

def print_sub(title):
    """
    Prints a smaller header with dashes for sub-sections.
    """
    print(f"\n --- {title} ---")

def load_csv(name, filename):
    """
    Loads a CSV file into a pandas DataFrame.
    
    Parameters:
    name: A simple name for logging (e.g., "patients")
    filename: The actual file name on disk (e.g., "patients.csv")
    
    Returns:
    The DataFrame if successful, or None if the file is missing.
    """
    filepath = os.path.join(CSV_FOLDER, filename)
    
    # Check if the file actually exists before trying to open it
    if not os.path.exists(filepath):
        print(f" [ERROR] File not found: {filepath}")
        return None
    
    # encoding="utf-8-sig" handles special characters that Windows sometimes adds
    df = pd.read_csv(filepath, encoding="utf-8-sig")
    
    # Print how many rows and columns we loaded so we know it worked
    print(f" Loaded {name}: {len(df):,} rows x {len(df.columns)} columns")
    return df

def check_nulls(df, name):
    """
    Checks every column for missing values (Nulls, NaN, or empty strings).
    """
    print_sub("Null Check")
    
    # Count standard nulls (NaN/None)
    null_counts = df.isnull().sum()
    
    # Also check for empty strings in text columns
    for col in df.select_dtypes(include=["object", "string"]).columns:
        empty_count = (df[col].str.strip() == "").sum()
        if empty_count > 0:
            null_counts[col] += empty_count
            
    # Filter to only show columns that actually have nulls
    has_nulls = null_counts[null_counts > 0]
    
    if has_nulls.empty:
        print(f" No null values found in {name}.")
    else:
        for col, count in has_nulls.items():
            pct = (count / len(df)) * 100
            print(f" [NULL] {col}: {count} nulls ({pct:.1f}%)")

def check_data_types(df, name):
    """
    Shows what data type pandas guessed for each column.
    Important: Dates often load as 'object' (string), which we need to fix later.
    """
    print_sub("Column Types (as Pandas reads them)")
    for col in df.columns:
        dtype = str(df[col].dtype)
        sample = df[col].iloc[0] # Grab the first value as an example
        print(f"    {col:<40} {dtype:<12} e.g. {repr(sample)}")

def check_large_number(df, name):
    """
    Checks if any number is too big for a standard SQL INT column.
    SQL INT max is ~2.1 billion. If our ID is bigger, we need BIGINT.
    """
    INT_MAX = 2_147_483_647
    print_sub("Large Number Check (SQL INT max = 2,147,483,647)")
    
    # Look only at columns that pandas thinks are numbers
    int_cols = df.select_dtypes(include=['int64', "float64"]).columns
    
    for col in int_cols:
        col_max = df[col].max()
        if col_max > INT_MAX:
            print(f"    [WARN] {col}: max value = {col_max:,} -> needs BIGINT in SQL")
        else:
            print(f"    [OK] {col}: max value = {col_max:,} -> INT is fine")

def check_categorical_values(df, name, cols):
    """
    Lists all unique values in specific columns. 
    Useful for finding typos (like 'Approvd' instead of 'Approved').
    """
    print_sub("Categorical Value Check")
    for col in cols:
        if col not in df.columns:
            print(f"    [WARN] Column '{col}' not found in {name}. Skipping.")
            continue
            
        value_counts = df[col].value_counts()
        print(f" Column: {col}")
        for val, count in value_counts.items():
            pct = (count / len(df)) * 100
            print(f" '{val}': {count} rows ({pct:.1f}%)")

def check_date_column(df, col_name):
    """
    Tries to convert a column to dates. If it fails, it tells us which rows are bad.
    """
    if col_name not in df.columns:
        return
        
    # errors='coerce' turns bad dates into NaT (Not a Time) instead of crashing
    parsed = pd.to_datetime(df[col_name], errors='coerce')
    
    bad_count = parsed.isnull().sum()
    if bad_count > 0:
        print(f"    [FAIL] {col_name}: {bad_count} rows have unparseable dates")
        bad_vals = df[col_name][parsed.isnull()].unique()
        print(f"      Example bad values: {list(bad_vals[:5])}")
    else:
        min_date = parsed.min().strftime("%Y-%m-%d")
        max_date = parsed.max().strftime("%Y-%m-%d")
        print(f"    [OK] {col_name}: all valid | range: {min_date} -> {max_date}")

def check_doctors_other_branches(df):
    """
    The 'Other Branches Visited' column is a string that looks like a list: "['FR33', 'MA60']".
    We use ast.literal_eval to turn it into a real Python list so we can split it into separate rows.
    """
    col = 'Other Branches Visited'
    if col not in df.columns:
        print(f"    [WARN] Column '{col}' not found in doctors dataset. Skipping.")
        return
        
    unpacked_rows = []
    parse_errors = 0
    
    # Loop through every row in the doctors table
    for _, r in df.iterrows():
        raw_value = r[col]
        doctor_id = r['Doctor ID'] 
        
        try:
            # Turn the string "['A', 'B']" into a real list ['A', 'B']
            branch_list = ast.literal_eval(raw_value)
            
            for branch_id in branch_list:
                unpacked_rows.append({
                    "doctor_id": doctor_id,
                    "branch_id": branch_id.strip() 
                })
        except (ValueError, SyntaxError):
            parse_errors += 1
            
    print(f"    Raw column type: string (e.g. {repr(df[col].iloc[0])})")
    print(f"    Parse errors: {parse_errors}")
    print(f"    Total (doctor, branch) pairs unpacked: {len(unpacked_rows)}")
    
    if unpacked_rows:
        unpacked_df = pd.DataFrame(unpacked_rows)
        unique_branches = unpacked_df['branch_id'].nunique()
        print(f"    Unique branch IDs referenced: {unique_branches}")
        print(f"\n    Preview of unpacked doctor_branch_visits table:")
        print(f"    {'doctor_id':<15} {'branch_id'}")
        print(f"    {'-'*25}")
        for _, r in unpacked_df.head(8).iterrows():
            print(f"    {r['doctor_id']:<15} {r['branch_id']}")
        print(f"    ... ({len(unpacked_rows)} total rows)")
        print(f"\n    -> IN ETL: drop this column from doctors table, ")
        print(f"      create separate 'doctor_branch_visits' table instead.")

def check_yes_no_column(df, name, yes_no_column):
    """
    Checks if a column only contains 'Yes' and 'No'. 
    We need this because in SQL we will convert them to 1 and 0 (BIT type).
    """
    print_sub(f"Yes/No Col Verification: {yes_no_column}")
    if yes_no_column not in df.columns:
        return
        
    # Get all unique values, make them lowercase to ignore case differences
    unique_vals = set(df[yes_no_column].str.strip().str.lower().unique())
    expected = {"yes", "no"}
    unexpected = unique_vals - expected
    
    if unexpected:
        print(f" {yes_no_column}: unexpected values found: {unexpected}")
    else:
        count_yes = (df[yes_no_column].str.lower() == "yes").sum()
        count_no = (df[yes_no_column].str.lower() == "no").sum()
        print(f" {yes_no_column}: Yes= {count_yes}, No= {count_no}")

def check_fk_integrity(child_df, child_col, parent_df, parent_col, label):
    """
    Checks Referential Integrity: Do all IDs in the child table exist in the parent table?
    Example: Does every Patient ID in 'appointments' exist in 'patients'?
    """
    child_ids = set(child_df[child_col].unique())
    parent_ids = set(parent_df[parent_col].unique())
    
    # Find IDs that are in child but NOT in parent (orphans)
    orphans = child_ids - parent_ids
    
    if orphans:
        print(f" {label}: {len(orphans)} orphan IDs found")
        print(f" Example Orphans: {list(orphans)[:5]}")
    else:
        print(f" {label}: All {len(child_ids)} IDs exist in parent table")

# --- MAIN PROFILING LOGIC ---

def main():
    """
    The main function that runs all the checks in order.
    """
    print_header("HOSPITAL DATA PROFILING REPORT")
    print(f"  Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Folder: {os.path.abspath(CSV_FOLDER)}")

    # STEP 1: Load all files into a dictionary called 'dfs'
    print_header("Step 1: Load CSV Files")
    dfs = {} 
    for name, filename in FILES.items():
        df = load_csv(name, filename)
        if df is not None:
            dfs[name] = df  # Store the dataframe using the simple name as the key
            
    total_rows = sum(len(df) for df in dfs.values())
    print(f"\nTotal rows loaded across all datasets: {total_rows:,}")

    # STEP 2: Null Checks
    print_header("Step 2: Null Value Checks")
    for name, df in dfs.items():
        print(f"\n [{name}]")
        check_nulls(df, name)

    # STEP 3: Data Type Checks
    print_header("Step 3: Data Type Checks")
    for name, df in dfs.items():
        print(f"\n [{name}]")
        check_data_types(df, name)
    
    # STEP 4: Large Integer Detection
    print_header("STEP 4: LARGE INTEGER CHECK (affects SQL column type choice)")
    print("\n  [billing.csv] — Claim ID and Case ID are the suspected ones")
    if "billing" in dfs:
        check_large_number(dfs["billing"], "billing")

    # STEP 5: Categorical Value Checks
    print_header("STEP 5: CATEGORICAL VALUES AUDIT")
    
    print("\n  [surgeries] — Surgery Outcome, Anesthesia Type")
    if "surgeries" in dfs:
        check_categorical_values(dfs["surgeries"], "surgeries", ["Surgery Outcome", "Anesthesia Type"])
        
    print("\n  [prescriptions] -- Pharmacy Availability")
    if "prescriptions" in dfs:
        check_categorical_values(dfs['prescriptions'], 'prescriptions', ["Pharmacy Availability"])
        
    print("\n  [patients] — Admission, Surgery Underwent")
    if "patients" in dfs:
        check_categorical_values(dfs['patients'], "patients", ["Admission", "Surgery Underwent"])

    # STEP 6: Date Validation
    print_header("STEP 6: DATE VALIDATION")
    date_col_map = {
        "appointments": ["Date of Consultation"],
        "patients": ["Date of Registration", "Date of First Consultation", "Date of Latest Consultation"],
        "surgeries": ["Surgery Date"],
        "prescriptions": ["Issued Date"],
        "lab_reports": ["Test Date"]
    }
    
    for table_name, cols in date_col_map.items():
        if table_name not in dfs:
            continue
        print(f"\n  [{table_name}]")
        for col in cols:
            check_date_column(dfs[table_name], col)

    # STEP 7: Yes/No Column Verifications
    print_header("STEP 7: YES/NO COLUMNS (will become BIT in SQL)")
    yes_no_map = {
        "branches": ["OT_Available", "Inhouse Anesthetician", "Inhouse Pharmacy", "Inhouse Nutritionist", "Luxury Suite Rooms", "Prayer Room", "Kids Play Area"],
        "patients": ["Admission", "Surgery Underwent"],
        "appointments": ["Followup Required", "Nutritionist Recommended"],
        "prescriptions": ["Pharmacy Availability"],
    }

    for table_name, cols in yes_no_map.items():
        if table_name not in dfs:
            continue
        print(f"\n  [{table_name}]")
        for col in cols:
            check_yes_no_column(dfs[table_name], table_name, col)

    # STEP 8: Doctors List-String Problem
    print_header("STEP 8: DOCTORS - LIST-STRING COLUMN ANALYSIS")
    if "doctors" in dfs:
        check_doctors_other_branches(dfs["doctors"])

    # STEP 9: Foreign Key Integrity Checks
    print_header("STEP 9: FOREIGN KEY INTEGRITY CHECKS")
    
    # List of tuples: (child_table, child_col, parent_table, parent_col, label)
    fk_checks = [
        ("appointments", "Patient ID", "patients", "Patient ID", "appointments.Patient ID -> patients.Patient ID"),
        ("appointments", "Branch ID", "branches", "Branch ID", "appointments.Branch ID -> branches.Branch ID"),
        ("appointments", "Consulted Doctor ID", "doctors", "Doctor ID", "appointments.Consulted Doctor ID -> doctors.Doctor ID"),
        ("billing", "Patient ID", "patients", "Patient ID", "billing.Patient ID -> patients.Patient ID"),
        ("surgeries", "Patient ID", "patients", "Patient ID", "surgeries.Patient ID -> patients.Patient ID"),
        ("surgeries", "Doctor ID", "doctors", "Doctor ID", "surgeries.Doctor ID -> doctors.Doctor ID"),
        ("prescriptions", "Patient ID", "patients", "Patient ID", "prescriptions.Patient ID -> patients.Patient ID"),
        ("lab_reports", "Patient ID", "patients", "Patient ID", "lab_reports.Patient ID -> patients.Patient ID"),
    ]

    for child_name, child_col, parent_name, parent_col, label in fk_checks:
        if child_name in dfs and parent_name in dfs:
            check_fk_integrity(
                dfs[child_name], child_col,
                dfs[parent_name], parent_col,
                label
            )

    # STEP 10: Business Logic Check (Requested vs Consulted Doctor)
    print_header("STEP 10: BUSINESS LOGIC CHECK — REQUESTED vs CONSULTED DOCTOR")
    if "appointments" in dfs:
        df_appt = dfs["appointments"]
        mismatches = (df_appt['Requested Doctor ID'] != df_appt['Consulted Doctor ID']).sum()
        pct = (mismatches / len(df_appt)) * 100
        print(f"\n  Appointments where consulted != requested: "
              f"{mismatches:,} / {len(df_appt):,} ({pct:.1f}%)")
        if mismatches == len(df_appt):
            print("  -> ALL appointments have a different consulted doctor.")
            print("  -> This is the intended data design — not an error.")
            print("  -> Insight: useful for 'doctor substitution rate' reports.")

if __name__ == "__main__":
    main()