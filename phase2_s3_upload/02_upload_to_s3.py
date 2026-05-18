import boto3 #           # The official AWS library for Python. Think of it as the "driver" that lets Python talk to AWS.
import os
from dotenv import load_dotenv
from pathlib import Path 

load_dotenv() # Load environment variables from a .env file. This is a common practice to keep sensitive information like AWS credentials out of your code.

#Configuration 
CSV_FOLDER = Path(r"D:\data_ENGG_PROJ\hospital-etl-aws\data\raw")

S3_BUCKET = os.getenv("S3_BUCKET_NAME")

S3_PREFIX = "raw/"
# WHY a prefix? S3 doesn’t have real folders. It has "keys" (filenames).
# By adding "raw/", we create a virtual folder structure. 
# File becomes: raw/appointments.csv instead of just appointments.csv.
# This keeps our bucket organized (raw/ vs processed/ vs reports/).

AWS_REGION =os.getenv("AWS_REGION",'ap-south-1')

# List of CSV files to upload
FILES = [
    "appointments.csv", "billing.csv", "patients.csv",
    "doctors.csv", "surgeries.csv", "prescriptions.csv",
    "lab_reports.csv", "branches.csv"
]

def get_s3_client():
    """ Creates an S3 client using credentials from environment variables
    """
    return boto3.client("s3",region_name=AWS_REGION)
        # HOW IT WORKS:
    # boto3 looks for AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in your environment.
    # load_dotenv() put them there earlier.
    # It returns a "client" object. Think of this client as a remote control for S3.


def upload_file_to_s3(s3_client,local_path, bucket,s3_key):
    """
    uploads one files to s3
    """
    file_size = os.path.getsize(local_path)

    print(f"Uploading {os.path.basename(local_path)} ({file_size/1024:.1f} KB) -> s3://{bucket}/{s3_key})")

    s3_client.upload_file(local_path,bucket,s3_key)
    # WHAT THIS DOES:
    # 1. Opens local_path on your computer.
    # 2. Streams it over the internet to AWS.
    # 3. Saves it in 'bucket' with the name 's3_key'.
    # 4. Handles retries automatically if the network blips.

    print(F" Done")

def verify_upload(s3_client, bucket, prefix):
    """
    Lists all objects in the bucket under raw/ to confirm uploads.
    """
    print(f"\n  Verifying — listing all objects in s3://{bucket}/{prefix}")
    
    # THE CORE LINE:
    response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    # WHAT THIS DOES:
    # Asks S3: "Give me a list of all files that start with 'raw/'".
    # Returns a dictionary with metadata (Key, Size, LastModified).

    if "Contents" not in response:
        # WHY check this? If the folder is empty, "Contents" key won't exist in the response.
        # Without this check, the next line would crash with a KeyError.
        print("  No files found — something went wrong")
        return

    total_size = 0
    for obj in response["Contents"]:
        size_kb = obj["Size"] / 1024
        print(f"    {obj['Key']:<45} {size_kb:.1f} KB")
        total_size += obj["Size"]

    print(f"\n  Total: {len(response['Contents'])} files, {total_size/1024:.1f} KB")
    # WHY sum sizes? To ensure no partial uploads occurred.


def main():
    # ADD THESE TWO LINES FOR DEBUGGING:
    print(f"Current Working Directory: {os.getcwd()}")
    print(f"Looking for data at: {Path(CSV_FOLDER).resolve()}")

    print("=" * 55)
    print(" PHASE 2 — S3 UPLOAD")
    print("=" * 55)

    s3 = get_s3_client() # Get our remote control
    uploaded = 0         # Counter to track success

    # LOOP THROUGH EACH FILE
    for filename in FILES:
        local_path = CSV_FOLDER / filename
        # WHY join? Don't use strings like CSV_FOLDER + "/" + filename.
        # os.join handles Windows (\) vs Linux (/) slashes automatically.

        if not os.path.exists(local_path):
            # DEFENSIVE CODING: Check if file exists BEFORE trying to upload.
            # Prevents a confusing "FileNotFoundError" deep in the boto3 library.
            print(f"  [ERROR] Not found: {local_path}")
            continue # Skip this file, move to next

        # CONSTRUCT THE S3 KEY
        s3_key = f"{S3_PREFIX}{filename}"
        # Example: "raw/appointments.csv"
        
        # CALL THE HELPER
        upload_file_to_s3(s3, local_path, S3_BUCKET, s3_key)
        uploaded += 1

    print(f"\n  Uploaded {uploaded}/8 files")
    
    # VERIFY
    verify_upload(s3, S3_BUCKET, S3_PREFIX)

    print("\n  NEXT: Take a screenshot of the S3 bucket in AWS console.")


if __name__ == "__main__":
    main()