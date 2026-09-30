-- q01: partition filter template
SELECT business_date, COUNT(*) AS sales_rows, SUM(sales_amount) AS sales_amount
FROM fact_sales
WHERE business_date BETWEEN DATE '2026-01-01' AND DATE '2026-01-07'
GROUP BY business_date
ORDER BY business_date;
