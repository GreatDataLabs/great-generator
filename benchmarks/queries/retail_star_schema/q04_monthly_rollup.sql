-- q04: monthly rollup template
SELECT d.month_id, SUM(f.sales_amount) AS sales_amount, COUNT(*) AS sales_rows
FROM fact_sales f
JOIN dim_date d ON f.date_id = d.date_id
GROUP BY d.month_id
ORDER BY d.month_id;
