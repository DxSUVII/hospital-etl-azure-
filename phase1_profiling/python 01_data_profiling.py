import pandas 
import ast    # Python's built-in module to safely evaluate
                         # strings that look like Python code.

import os 
from datetime import datetime 

CSV_FOLDER ="."
FILES={
    "appointments"  : "appointments.csv",
    "billing"       : "billing.csv",
    "patients"      : "patients.csv",
    "doctors"       : "doctors.csv",
    "surgeries"     : "surgeries.csv",
    "prescriptions" : "prescriptions.csv",
    "lab_reports"   : "lab_reports.csv",
    "branches"      : "branches.csv",
}

# ---HELPER FUNCTIONS---
def print_header(title):
    """
    print a formatted header for better readability in the console output.
    """
    print("\n" + "="* 60)
    print(f" {title}")
    print("=" * 60)


def print_sub(title):
    """
    print a smaller section divider
    """
    print("\n --- {title}---")


def load_csv(name,filename):
    """
    Loads a single csv not pandas DF.

    parameters:
    name: str - the name of the dataset (for logging purposes)
    filename: str - the name of the csv file to load

    returns:
         DataFrame if successful, None if there was an error.
    """
    filepath = os.path.join(CSV_FOLDER,filename)
    # always check file existence before trying to load it
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        return None
    
    df = pd.read_csv(filepath,encoding="utf-8-sig")
    return df

    print(F"Loded {name}: {len(df):,} rows X {len(df.columns)} columns")
    return df 

def check_nulls(df,name):
    """
    check every columns for null values 
    we check for all three:
    - isnull() catches NaN and None 
    - catches empty strings 
    """
    print_sub("null check")

    null_counts = df.isnull().sum()
    for col in df.select_dtypes(include=["object"]).columns:
        empty_count =(df[col].str.strip() =="").sum()
        if empty_count >0:
            null_counts[col]+= empty_count
    
    has_nulls=null_counts[null_counts>0]

    if has_nulls.empty:
        print(f" No null values found in {name}.")
    else:
        for col,count in has_nulls.items():
            pct = (count/len(df))* 100
            print(F" x {col}:{count} nulls ({pct:.1f}%)")
            



def check_data_types(df,name):
    """
    shows the infered data type of each column

    Dates like "4/2/2021" load as 'object' (string), not as actual dates.
    Numbers like Claim ID load as int64, but we need to check if they're
    too large for SQL INT (max: 2,147,483,647)
    """
    print_sub("Column Types (as Pandas reads them)")
    for col in df.columns:
        dtype = str(df[col].dtype)
        sample = df[col].iloc[0]
        print(f"    {col:<40} {dtype:<12} e.g. {repr(sample)}")

def check_large_number(df,name):
    """
     Specifically checks if any integer column exceeds SQL INT max.

      SQL INT holds up to 2,147,483,647 (about 2.1 billion).
    SQL BIGINT holds up to 9,223,372,036,854,775,807.
 
    If a value like 9,786,462,894 lands in an INT column in SQL,
    it will either error out or silently corrupt to a wrong number.
    BIGINT is the safe choice for ID columns.

     """
    INT_MAX = 2_147_483_647
    print_sub("Large Number Check (for SQL INT max =2_147_483_647 )")

    # select only num colms that pandas loaded as integers 
    int_cols = df.select_dtypes(include=['int64',"float64"]).columns
    for col in int_cols:
        col_max = df[col].max()
        if col_max > INT_MAX:
           print(f"    ⚠ {col}: max value = {col_max:,} → needs BIGINT in SQL")
        else:
            print(f"    ✓ {col}: max value = {col_max:,} → INT is fine")


def check_catogorical_values(df,name,cols):
    """

     For columns with a known set of expected values (categories),
    show every unique value and its count.
 
    Why? 
    - Catches typos: "Approvd" instead of "Approved"
    - Catches extra categories you didn't know about (like "Pending")
    - Confirms Yes/No columns don't have "yes", "YES", "Y" mixed in
 
    Parameters:
        cols : list of column names to check
    """
    print_sub("categorical value check")
    for col in cols:
        if col not in df.columns:
            print(f"    ⚠ Column '{col}' not found in {name}. Skipping.")
            continue
        value_counts =df[col].value_counts()
        print(f" column: {col}")
        for val,count in value_counts.items():
            pct = (count/len(df))*100
            print(f" '{val}': {count} rows ({pct:.1f}%)") 



def check_date_column(df,col_name):
    """
    Validates date columns and checks for format consistency

    Our dates look like '4/2/2021' (M/D/YYYY format).
    We use pd.to_datetime with errors='coerce' — this means:
    - Valid dates → converted to a proper datetime object
    - Invalid dates → turned into NaT (Not a Time, pandas version of null)

    If any NaT values appear, those rows have unparseable dates.
    """
    if col_name not in df.columns:
        return
    parsed = pd.to_datetime(df[col_name],errors='coerce')

    bad_count = parsed.isnull().sum()
    if bad_count >0:
        print(f"    ✗ {col_name}: {bad_count} rows have unparseable dates")
        bad_vals = df[col_name][parsed.isnull()].unique()
        print(f"      Example bad values: {list(bad_vals[:5])}")
    else:
        min_date = parsed.min().strftime("%Y-%m-%d")
        max_date = parsed.max().strftime("%Y-%m-%d")
        print(f"    ✓ {col_name}: all valid | range: {min_date} → {max_date}")
   
    

    def check_doctors_other_branches(df):
        """
            The column contains strings like: ['FR33', 'MA60', 'ST89']
        These look like Python lists but they're just text in the CSV.
    
        ast.literal_eval() safely evaluates a string that looks like
        a Python literal (list, dict, number, string) and returns
        the actual Python object.


        For example:
        ast.literal_eval("['FR33', 'MA60']")
        → ['FR33', 'MA60']   (actual Python list)
 
        We do NOT use eval() — it runs arbitrary Python code and is
        a security risk. ast.literal_eval() only handles data, not code.
    
        This function:
        1. Parses each string into an actual list
        2. Counts how many branch visits each doctor has
        3. Collects all unique branch IDs mentioned
        4. Shows a preview of what the unpacked table would look like
        """
        col = 'Other Brnaches visited'
        if col not in df.columns:
            print(f"    ⚠ Column '{col}' not found in doctors dataset. Skipping.")
            return
        # we will build the unpacked table: one row per (docter ID ,Branch ID)
        unpacked_rows =[]
        parse_errors = 0
        
        for _,r in df.iterrows():
            raw_value = row[col]
            doctor_id = row['Docter ID']
            try:
                branch_list =ast.literal_eval(raw_value)

                for branch_id in branch_list:
                    unpacked_rows.append({
                        "docter_id": doctor_id,
                        "branch_id": branch_id.strip() 
                    })
            except(ValueError,SyntaxError):
                # if the string ant be parsed count as error 
                parse_errors +=1

    print(f"    Raw column type: string (e.g. {repr(df[col].iloc[0])})")
    print(f"    Parse errors: {parse_errors}")
    print(f"    Total (doctor, branch) pairs unpacked: {len(unpacked_rows)}")
        
    if unpacked_rows:
        # convert to dataframe so we can summerise
        unpacked_df = pd.DataFrame(unpacked_rows)
        unique_branches = unpacked_df['branch_id'].nunique()
        print(f"    Unique branch IDs referenced: {unique_branches}")
        print(f"\n    Preview of unpacked doctor_branch_visits table:")
        print(f"    {'doctor_id':<15} {'branch_id'}")
        print(f"    {'-'*25}")
        for _, r in unpacked_df.head(8).iterrows():
            print(f"    {r['doctor_id']:<15} {r['branch_id']}")
        print(f"    ... ({len(unpacked_rows)} total rows)")
        print(f"\n    → IN ETL: drop this column from doctors table, ")
        print(f"      create separate 'doctor_branch_visits' table instead.")


     