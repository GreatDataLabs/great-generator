-- q02: fact-to-dimension join and aggregation template
SELECT c.region, p.product_category, COUNT(*) AS sales_rows, SUM(f.sales_amount) AS sales_amount
FROM fact_sales f
JOIN dim_customer c ON f.customer_id = c.customer_id
JOIN dim_product p ON f.product_id = p.product_id
GROUP BY c.region, p.product_category
ORDER BY sales_amount DESC;
