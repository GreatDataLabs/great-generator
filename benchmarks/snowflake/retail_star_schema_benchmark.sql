-- Snowflake retail star schema benchmark query templates.
-- Load synthetic benchmark tables through your own stage/COPY process before running.
-- These templates are not universal performance claims.

SELECT business_date, COUNT(*) AS sales_rows, SUM(sales_amount) AS sales_amount
FROM fact_sales
WHERE business_date BETWEEN DATE '2026-01-01' AND DATE '2026-01-07'
GROUP BY business_date
ORDER BY business_date;

SELECT c.region, p.product_category, COUNT(*) AS sales_rows, SUM(f.sales_amount) AS sales_amount
FROM fact_sales f
JOIN dim_customer c ON f.customer_id = c.customer_id
JOIN dim_product p ON f.product_id = p.product_id
GROUP BY c.region, p.product_category
ORDER BY sales_amount DESC;
