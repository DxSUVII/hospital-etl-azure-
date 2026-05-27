<div align="center">

<img src="https://img.shields.io/badge/AWS-Cloud%20Track-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white"/>
<img src="https://img.shields.io/badge/Status-Complete-22c55e?style=for-the-badge"/>
<img src="https://img.shields.io/badge/Region-ap--south--1-0ea5e9?style=for-the-badge&logo=amazonaws&logoColor=white"/>

# MetaData-Ingestion-Engine

### End-to-end data engineering pipeline: 8 CSVs → S3 → RDS PostgreSQL → Lambda reports
#### Internship Project · Rubixie Data Engineering Cloud Track

<br/>

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![AWS S3](https://img.shields.io/badge/AWS_S3-Storage-FF9900?style=flat-square&logo=amazons3&logoColor=white)](https://aws.amazon.com/s3)
[![AWS RDS](https://img.shields.io/badge/AWS_RDS-Database-527FFF?style=flat-square&logo=amazonrds&logoColor=white)](https://aws.amazon.com/rds)
[![AWS Lambda](https://img.shields.io/badge/AWS_Lambda-Serverless-FF9900?style=flat-square&logo=awslambda&logoColor=white)](https://aws.amazon.com/lambda)
[![EventBridge](https://img.shields.io/badge/EventBridge-Scheduler-E7157B?style=flat-square&logo=amazonaws&logoColor=white)](https://aws.amazon.com/eventbridge)
[![pandas](https://img.shields.io/badge/pandas-Transform-150458?style=flat-square&logo=pandas&logoColor=white)](https://pandas.pydata.org)

</div>

---

## 📌 Overview

This project builds a **production-style cloud ETL pipeline** for a multi-branch hospital system. Raw CSV data is profiled, uploaded to **Amazon S3**, transformed using **pandas + SQLAlchemy**, and loaded into **Amazon RDS PostgreSQL**. A **Lambda function** triggered by **EventBridge** generates daily analytical reports automatically.

> **37,600 rows · 8 source files · 9 RDS tables · 6 analytical queries · 1 automated daily report**

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  SOURCE                                                             │
│  8 CSV files · 37,600 rows · Local machine                         │
│  appointments · billing · patients · doctors ·                      │
│  branches · surgeries · prescriptions · lab_reports                 │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ boto3 upload
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STORAGE  ·  Amazon S3 — hospital-etl-data-suviii-2026             │
│                                                                     │
│   📁 raw/          📁 processed/       📁 reports/                 │
│   8 source CSVs    ETL staging         daily_report_*.csv          │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ read via boto3
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  TRANSFORM  ·  Python ETL — pandas + SQLAlchemy                    │
│                                                                     │
│   🔄 Cast types        📝 Rename cols      🔗 Unpack lists         │
│   DATE · BIGINT · BOOL  snake_case          doctor_branch_visits    │
│                                                                     │
│                    📦 Load order: dims → facts                      │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ to_sql() insert
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  SERVE  ·  Amazon RDS — PostgreSQL · hospital-etl-db · ap-south-1  │
│                                                                     │
│   Dimension tables          Fact tables             Total           │
│   branches (100)            appointments (12,000)   37,984 rows     │
│   doctors  (200)            billing      (5,000)    9 tables        │
│   patients (2,300)          surgeries    (1,500)                    │
│   doctor_branch_visits(384) lab_reports  (7,500)                    │
│                             prescriptions(9,000)                    │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ cron(0 9 * * ? *)
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  REPORT  ·  AWS Lambda + Amazon EventBridge                        │
│                                                                     │
│   ƛ hospital-daily-report   🕘 09:00 UTC daily   📄 → S3 reports/ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Dataset

| Table | Type | Rows | Description |
|-------|------|-----:|-------------|
| `branches` | Dimension | 100 | Hospital branches, facilities, OT availability |
| `doctors` | Dimension | 200 | Specialization, qualification, surgery experience |
| `doctor_branch_visits` | Bridge | 384 | Unpacked many-to-many doctor↔branch relationships |
| `patients` | Dimension | 2,300 | Registration, satisfaction rating, visit history |
| `appointments` | Fact | 12,000 | Consultations, diagnosis, prescriptions, followup |
| `billing` | Fact | 5,000 | Claims, insurance coverage, out-of-pocket expenses |
| `surgeries` | Fact | 1,500 | Surgery type, outcome, duration, recovery |
| `lab_reports` | Fact | 7,500 | Test results, dates, case linkage |
| `prescriptions` | Fact | 9,000 | Medications, dosage, pharmacy availability |
| **Total** | | **37,984** | |

---

## 🗂️ Project Structure

```
hospital-etl-aws/
│
├── 📁 data/
│   ├── raw/                          ← original 8 CSVs (never modified)
│   └── processed/                    ← ETL output staging
│
├── 📁 phase1_profiling/
│   ├── 01_data_profiling.py          ← null checks, FK integrity, type audit
│   └── output/profiling_report.txt
│
├── 📁 phase2_s3_upload/
│   └── 02_upload_to_s3.py            ← boto3 upload + verification
│
├── 📁 phase3_etl/
│   ├── 03_create_tables.sql          ← PostgreSQL schema (DROP → CREATE)
│   └── 03_etl_pipeline.py            ← S3 read → transform → RDS load
│
├── 📁 phase4_sql/
│   └── 04_queries.sql                ← 6 analytical queries
│
├── 📁 phase5_reporting/
│   └── 05_report_generator.py        ← Lambda handler, daily CSV report
│
├── 📁 docs/
│   └── architecture_documents.docx
│
├── 📁 screenshots/                   ← AWS console + query execution evidence
│
├── .env                              ← credentials (gitignored ✅)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🔬 Phase Breakdown

<details>
<summary><b>Phase 1 — Data Profiling</b> &nbsp;|&nbsp; <code>01_data_profiling.py</code></summary>

<br/>

Comprehensive data quality audit before any transformation:

- **Null checks** — scanned all 8 datasets for NaN and empty strings
- **Data type validation** — dates were loading as `object` (string); flagged for casting
- **Large integer detection** — `claim_id` and `case_id` exceed SQL INT max (2,147,483,647); schema uses `BIGINT`
- **Categorical value audit** — verified surgery outcomes, claim statuses, yes/no columns for typos
- **Foreign key integrity** — 9 FK relationships verified, zero orphan IDs found
- **List-string unpacking** — `Other Branches Visited` stored as `"['BR01', 'BR02']"`; parsed via `ast.literal_eval` → 384-row bridge table
- **Business logic check** — 100% doctor substitution rate confirmed as intentional data design (not a data error)

</details>

<details>
<summary><b>Phase 2 — S3 Upload</b> &nbsp;|&nbsp; <code>02_upload_to_s3.py</code></summary>

<br/>

- Uploads all 8 CSVs to `s3://hospital-etl-data-suviii-2026/raw/`
- Credentials loaded from `.env` via `python-dotenv`
- Post-upload verification using `list_objects_v2` — confirms file count and total size
- Prefixed as `raw/` to create virtual folder structure in S3

</details>

<details>
<summary><b>Phase 3 — ETL Pipeline</b> &nbsp;|&nbsp; <code>03_etl_pipeline.py</code></summary>

<br/>

Reads from S3 → transforms in pandas → loads into RDS:

| Step | What happens |
|------|-------------|
| Read | `boto3.get_object` streams each CSV into `pd.read_csv` |
| Clean headers | Spaces/dots/hyphens → `snake_case` using regex |
| Cast booleans | `yes/no` strings → Python `bool` via `.isin(["yes"])` |
| Cast dates | `pd.to_datetime` with `errors="coerce"` |
| Cast integers | `claim_id`, `case_id` → `int64` (BIGINT in PostgreSQL) |
| Unpack list | `Other Branches Visited` → `doctor_branch_visits` table |
| Load order | Dimensions first, facts second (FK constraint safety) |
| Verify | `SELECT COUNT(*)` per table after load |

> **Why pandas instead of AWS Glue?**
> Glue Spark jobs cost $0.44–$0.88 minimum per run. For 5.4 MB of CSV data, pandas completes the same job in under 10 seconds at **zero cost**. Glue is the right choice at TB scale — this trade-off is documented in the architecture doc as a deliberate decision.

</details>

<details>
<summary><b>Phase 4 — SQL Analytics</b> &nbsp;|&nbsp; <code>04_queries.sql</code></summary>

<br/>

Six analytical queries executed in **AWS CloudShell** against RDS PostgreSQL:

| # | Query | Key Finding |
|---|-------|-------------|
| 1 | Monthly visits by branch | Multi-year time series from 2020 onwards |
| 2 | Revenue vs insurance coverage by branch | CL09 top branch: ~₹1.38Cr total revenue |
| 3 | Top 10 diagnoses | Arthritis #1 at 10.50% frequency |
| 4 | Surgery outcomes by doctor | Success rates range 0%–71% across surgeons |
| 5 | Doctor substitution rate per branch | 100% substitution — confirmed as design intent |
| 6 | Claim status by insurance provider | Blue Cross leads approvals at 35.54% |

</details>

<details>
<summary><b>Phase 5 — Automated Reporting</b> &nbsp;|&nbsp; <code>05_report_generator.py</code></summary>

<br/>

- Deployed as **AWS Lambda** function (`hospital-daily-report`)
- **EventBridge schedule**: `cron(0 9 * * ? *)` — fires every day at 09:00 UTC
- Runs all 6 analytical queries against RDS on each invocation
- Combines results into a single structured CSV file
- Saves output to `s3://hospital-etl-data-suviii-2026/reports/daily_report_YYYY-MM-DD.csv`
- Uses `AWSSDKPandas-Python311` Lambda layer (pandas + psycopg2 pre-bundled)
- Returns `{"statusCode": 200, "body": "Report saved to reports/daily_report_*.csv"}`

</details>

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- AWS account (S3 + RDS access)
- PostgreSQL client (psql / DBeaver / AWS CloudShell)

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/hospital-etl-aws.git
cd hospital-etl-aws

# Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

### Environment Setup

Create a `.env` file in the project root (already gitignored):

```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=ap-south-1
S3_BUCKET_NAME=your-bucket-name

RDS_HOST=your-rds-endpoint.rds.amazonaws.com
RDS_PORT=5432
RDS_DB_NAME=postgres
RDS_USER=postgres
RDS_PASSWORD=your_password
```

### Run the Pipeline

```bash
# Step 1 — Profile raw data quality
python phase1_profiling/01_data_profiling.py

# Step 2 — Upload CSVs to S3
python phase2_s3_upload/02_upload_to_s3.py

# Step 3 — Run ETL: S3 → transform → RDS
python phase3_etl/03_etl_pipeline.py

# Step 4 — Run SQL analytics (CloudShell or DBeaver)
# psql -h <RDS_HOST> -U postgres -d postgres -f phase4_sql/04_queries.sql

# Step 5 — Test Lambda report locally
python phase5_reporting/05_report_generator.py
```

### Expected ETL Output

```
=== Live RDS Row Counts ===
  branches                    100 rows
  doctors                     200 rows
  doctor_branch_visits        384 rows
  patients                  2,300 rows
  appointments             12,000 rows
  billing                   5,000 rows
  surgeries                 1,500 rows
  lab_reports               7,500 rows
  prescriptions             9,000 rows
```

---

## 🛠️ Tech Stack

| Category | Technology | Purpose |
|----------|-----------|---------|
| Language | Python 3.13 | All pipeline scripts |
| Transformation | pandas 2.2 + SQLAlchemy 2.0 | Data wrangling + DB ORM |
| Cloud Storage | Amazon S3 | Raw CSVs + daily reports |
| Cloud Database | Amazon RDS PostgreSQL 15 | Relational data warehouse |
| Serverless | AWS Lambda | Report generation function |
| Scheduling | Amazon EventBridge | Daily cron trigger |
| AWS SDK | boto3 1.38 | S3 + AWS service operations |
| DB Driver | psycopg2-binary | PostgreSQL connectivity |
| Config | python-dotenv | Credential management |
| Data Generation | Faker 37 | Synthetic dataset creation |

---

## 🔑 Key Design Decisions

**🔗 Bridge table for doctors ↔ branches**
> The raw CSV stored branch visits as a Python list-string `"['BR01', 'BR02']"`. Profiling revealed this with `ast.literal_eval` — it was unpacked into a proper `doctor_branch_visits` bridge table during ETL for correct relational joins.

**🔢 BIGINT for large IDs**
> Data profiling detected that `claim_id` and `case_id` exceed the SQL INT maximum (2,147,483,647). Schema declares these as `BIGINT` to prevent silent overflow on insert.

**✅ Boolean casting from yes/no**
> Eleven yes/no columns across 4 tables are cast to PostgreSQL `BOOLEAN` during ETL — enabling efficient `WHERE` filtering and `SUM(CASE WHEN ...)` aggregations in analytics queries.

**📦 Dimension-first load order**
> Fact tables reference dimensions via foreign keys. Loading dimensions before facts prevents FK violations without requiring constraint disabling.

**💰 pandas over AWS Glue**
> Cost-conscious decision for a 5.4 MB dataset. Glue minimum billing is $0.44–$0.88/run regardless of data size. Fully documented in `architecture_documents.docx`. Glue is the correct production choice at TB scale.

---

## 📸 Evidence & Screenshots

| | Screenshot | What it shows |
|--|-----------|--------------|
| 🏗️ | !<img width="525" height="458" alt="architecture-s3" src="https://github.com/user-attachments/assets/e3741c54-f0e9-4a53-adb6-6774d16134b9" />
 | Full pipeline architecture diagram |
| 🪣 | ![S3]<img width="1360" height="461" alt="s3_bucket" src="https://github.com/user-attachments/assets/f6bfabbc-cc13-408e-874a-35538cc5f068" />
 | S3 bucket with `raw/` and `reports/` folders |
| 🗄️ | ![RDS]<img width="1360" height="414" alt="rds_instance_running" src="https://github.com/user-attachments/assets/52a015e9-8205-4bdb-a60f-c379d27cc048" />
 | RDS PostgreSQL instance — Available status |
| 📊 | ![ETL]<img width="1361" height="551" alt="tables_and_row_counts" src="https://github.com/user-attachments/assets/548e2027-cb85-4c38-999f-4ef3856d7b88" />
 | Post-load row count verification (all 9 tables) |
| 📋 | ![Schema]<img width="736" height="257" alt="REFRENCE" src="https://github.com/user-attachments/assets/eeb6d326-af35-4a28-bc04-1190696620d7" />
 | Table schema with data types from RDS |

| ƛ | ![Lambda] <img width="1358" height="497" alt="lamda_function_output" src="https://github.com/user-attachments/assets/e09a7e92-3858-4a7a-a32c-b8d5e69d9063" />
 | Lambda execution — Status 200 |
| 🕘 | ![EventBridge]<img width="1365" height="489" alt="cloudwatch_shedule " src="https://github.com/user-attachments/assets/9a36d0ae-7202-4c4b-8b68-1a780547c273" />
| EventBridge schedule — Enabled |

---

## 📄 License

Built as part of an internship submission for the **Rubixie Data Engineering Cloud Track**.

---

<div align="center">

**Built on AWS Free Tier &nbsp;·&nbsp; ap-south-1 (Mumbai) &nbsp;·&nbsp; May 2026**

⭐ *If you found this project useful, consider giving it a star!*

</div>now 
