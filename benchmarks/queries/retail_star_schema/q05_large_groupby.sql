-- q05: larger group-by behavior template
SELECT c.region, s.store_type, p.product_category, f.sales_channel,
       COUNT(*) AS sales_rows,
       SUM(f.quantity) AS quantity,
       SUM(f.sales_amount) AS sales_amount
FROM fact_sales f
JOIN dim_customer c ON f.customer_id = c.customer_id
JOIN dim_store s ON f.store_id = s.store_id
JOIN dim_product p ON f.product_id = p.product_id
GROUP BY c.region, s.store_type, p.product_category, f.sales_channel
ORDER BY sales_amount DESC;
