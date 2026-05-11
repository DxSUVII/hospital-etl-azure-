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
            



