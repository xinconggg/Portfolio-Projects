CREATE TABLE ap_gl_gold AS
SELECT t.*
FROM stg_ap_gl_transactions t
JOIN (
    SELECT transaction_id, MIN(transaction_date) AS min_date
    FROM stg_ap_gl_transactions
    WHERE vendor_id IS NOT NULL
      AND amount >= 0
    GROUP BY transaction_id
) AS first_tx
ON t.transaction_id = first_tx.transaction_id
   AND t.transaction_date = first_tx.min_date;
   
SELECT COUNT(*) FROM ap_gl_gold