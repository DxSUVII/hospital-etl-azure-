-- Run this entire file once in psql or DBeaver or the Python script below
-- Order matters: dimension tables first, fact tables second

-- ── DROP EXISTING TABLES (if re-running) ──────────────
DROP TABLE IF EXISTS prescriptions CASCADE;
DROP TABLE IF EXISTS lab_reports CASCADE;
DROP TABLE IF EXISTS surgeries CASCADE;
DROP TABLE IF EXISTS billing CASCADE;
DROP TABLE IF EXISTS appointments CASCADE;
DROP TABLE IF EXISTS doctor_branch_visits CASCADE;
DROP TABLE IF EXISTS doctors CASCADE;
DROP TABLE IF EXISTS patients CASCADE;
DROP TABLE IF EXISTS branches CASCADE;

-- ── DIMENSION TABLES ─────────────────────────────────────

CREATE TABLE IF NOT EXISTS branches (
    serial_no               INT,
    branch_id               VARCHAR(10)  PRIMARY KEY,
    location                VARCHAR(100),
    ot_available            BOOLEAN,
    inhouse_anesthetician   BOOLEAN,
    no_of_ots               INT,
    inhouse_pharmacy        BOOLEAN,
    inhouse_nutritionist    BOOLEAN,
    inpatient_rooms         INT,
    luxury_suite_rooms      BOOLEAN,
    prayer_room             BOOLEAN,
    kids_play_area          BOOLEAN
);

CREATE TABLE IF NOT EXISTS doctors (
    serial_no           INT,
    doctor_name         VARCHAR(100),
    doctor_id           VARCHAR(20)  PRIMARY KEY,
    specialization      VARCHAR(100),
    qualification       VARCHAR(20),
    surgery_experience  INT,
    practicing_branch   VARCHAR(10)
    -- Other Branches Visited intentionally excluded
    -- It is unpacked into doctor_branch_visits table instead
);

CREATE TABLE IF NOT EXISTS doctor_branch_visits (
    doctor_id   VARCHAR(20),
    branch_id   VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS patients (
    serial_no                       INT,
    patient_id                      VARCHAR(10)  PRIMARY KEY,
    date_of_registration            DATE,
    date_of_first_consultation      DATE,
    date_of_latest_consultation     DATE,
    overall_satisfaction_rating     INT,
    admission                       BOOLEAN,
    surgery_underwent               BOOLEAN,
    total_number_of_visits          INT
);

-- ── FACT TABLES ──────────────────────────────────────────

CREATE TABLE IF NOT EXISTS appointments (
    serial_no                INT,
    case_id                  BIGINT,
    patient_id               VARCHAR(10),
    branch_id                VARCHAR(10),
    date_of_consultation     DATE,
    requested_doctor_id      VARCHAR(20),
    consulted_doctor_id      VARCHAR(20),
    reason_for_visit         VARCHAR(200),
    diagnosis                VARCHAR(200),
    prescribed_medication    VARCHAR(200),
    followup_required        BOOLEAN,
    nutritionist_recommended BOOLEAN
);

CREATE TABLE IF NOT EXISTS billing (
    serial_no               INT,
    claim_id                BIGINT,
    patient_id              VARCHAR(10),
    case_id                 BIGINT,
    branch_id               VARCHAR(10),
    total_bill              DECIMAL(10,2),
    insurance_provider      VARCHAR(100),
    amount_covered          DECIMAL(10,2),
    out_of_pocket_expenses  DECIMAL(10,2),
    claim_status            VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS surgeries (
    serial_no               INT,
    case_id                 BIGINT,
    patient_id              VARCHAR(10),
    doctor_id               VARCHAR(20),
    branch_id               VARCHAR(10),
    surgery_type            VARCHAR(100),
    surgery_date            DATE,
    anesthesia_type         VARCHAR(20),
    surgery_outcome         VARCHAR(20),
    surgery_duration_hours  INT,
    recovery_period_days    INT
);

CREATE TABLE IF NOT EXISTS lab_reports (
    serial_no   INT,
    report_id   BIGINT,
    case_id     BIGINT,
    patient_id  VARCHAR(10),
    branch_id   VARCHAR(10),
    test_name   VARCHAR(100),
    test_date   DATE,
    result      VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS prescriptions (
    serial_no               INT,
    bill_id                 BIGINT,
    patient_id              VARCHAR(10),
    doctor_id               VARCHAR(20),
    medication_name         VARCHAR(100),
    dosage                  VARCHAR(20),
    quantity                INT,
    pharmacy_availability   BOOLEAN,
    issued_date             DATE
);