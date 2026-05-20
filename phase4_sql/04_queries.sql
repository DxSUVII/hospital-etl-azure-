-- Query 1: Monthly patient visits by branch
SELECT
    branch_id,
    COUNT(*) AS visits,
    TO_CHAR(date_of_consulation, 'YYYY-MM') AS month
FROM appointments
GROUP BY branch_id, TO_CHAR(date_of_consulation, 'YYYY-MM')
ORDER BY month, branch_id;

-- Query 2: Revenue vs Insurance Coverage by Branch (Fixed order by alias)
SELECT
    branch_id,
    COUNT(*) AS total_claims,
    ROUND(SUM(total_bill)::NUMERIC, 2) AS total_revnue,
    ROUND(SUM(amount_covered)::NUMERIC, 2) AS total_covered,
    ROUND(SUM(out_of_pocket_expensenes)::NUMERIC, 2) AS total_out_of_pocket
FROM billing
GROUP BY branch_id
ORDER BY total_revnue DESC;

-- Query 3: Top 10 diagnoses
SELECT
    diagnosis,
    COUNT(*) AS frequency,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM appointments), 2) AS pct
FROM appointments
GROUP BY diagnosis
ORDER BY frequency DESC
LIMIT 10;

-- Query 4: Surgery outcomes by doctor
SELECT
    doctor_id,
    COUNT(*) AS total_surgeries,
    SUM(CASE WHEN surgery_outcome = 'Successful'   THEN 1 ELSE 0 END) AS successful,
    SUM(CASE WHEN surgery_outcome = 'Failed'        THEN 1 ELSE 0 END) AS failed,
    SUM(CASE WHEN surgery_outcome = 'Complications' THEN 1 ELSE 0 END) AS complications,
    ROUND(SUM(CASE WHEN surgery_outcome = 'Successful' THEN 1 ELSE 0 END)
          * 100.0 / COUNT(*), 1) AS success_rate_pct
FROM surgeries
GROUP BY doctor_id
ORDER BY total_surgeries DESC
LIMIT 20;  

-- Query 5: Doctor Substitution Rate per Branch (Fixed table joins & typos)
SELECT 
    b.location AS branch_name,
    COUNT(a.serial_no) AS total_appointments,
    SUM(CASE WHEN a.requested_doctor_id <> a.consulted_doctor_id THEN 1 ELSE 0 END) AS substituted_appointments,
    ROUND(
        SUM(CASE WHEN a.requested_doctor_id <> a.consulted_doctor_id THEN 1 ELSE 0 END)::NUMERIC / COUNT(a.serial_no) * 100, 2) AS substitution_rate_pct
FROM appointments a
JOIN branches b ON a.branch_id = b.branch_id
GROUP BY b.location
ORDER BY substitution_rate_pct DESC;

-- Query 6: Claim Status by Insurance Provider
SELECT 
    insurance_provider,
    COUNT(claim_status) AS total_claims,
    COUNT(CASE WHEN claim_status = 'Approved' THEN 1 END) AS approved_claims,
    COUNT(CASE WHEN claim_status = 'Pending' THEN 1 END) AS pending_claims,
    COUNT(CASE WHEN claim_status = 'Rejected' THEN 1 END) AS rejected_claims,
    ROUND(
        (COUNT(CASE WHEN claim_status = 'Approved' THEN 1 END)::NUMERIC / 
         COUNT(claim_status)::NUMERIC) * 100, 
        2
    ) AS approved_rate_pct
FROM billing 
GROUP BY insurance_provider
ORDER BY approved_rate_pct DESC;