# Duplicate Check
CREATE TABLE dq_duplicates AS
SELECT transaction_id, COUNT(*) as duplicate_count
FROM stg_ap_gl_transactions
GROUP BY transaction_id
HAVING COUNT(*) > 1;

# Missing "vendor_id" Check
CREATE TABLE dq_missing_vendor AS
SELECT *
FROM stg_ap_gl_transactions
WHERE vendor_id IS NULL;

# Negative Amount Check
CREATE TABLE dq_negative_amount AS
SELECT *
FROM stg_ap_gl_transactions
WHERE amount < 0;

# Check Results
SELECT COUNT(*) FROM dq_duplicates;
SELECT COUNT(*) FROM dq_missing_vendor;
SELECT COUNT(*) FROM dq_negative_amount;