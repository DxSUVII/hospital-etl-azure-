import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv()

# Connect to database
conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)

cursor = conn.cursor()

# Read and execute SQL file
script_dir = Path(__file__).parent
sql_file = script_dir / "phase3_etl" / "03_create_tables.sql"

print(f"Reading SQL file from: {sql_file}")
print(f"File exists: {sql_file.exists()}")

if not sql_file.exists():
    raise FileNotFoundError(f"SQL file not found: {sql_file}")

with open(str(sql_file), "r") as f:
    sql_script = f.read()
    
    # Split statements by semicolon and execute individually
    statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]
    
    for i, statement in enumerate(statements, 1):
        print(f"Executing statement {i}/{len(statements)}...")
        cursor.execute(statement)

conn.commit()
cursor.close()
conn.close()

print("✓ Tables created successfully!")

print("✓ Tables created successfully!")