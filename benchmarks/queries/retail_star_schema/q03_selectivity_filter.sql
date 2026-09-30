-- q03: selective filter template
SELECT sales_channel, product_category, COUNT(*) AS sales_rows, AVG(sales_amount) AS avg_sales_amount
FROM fact_sales
WHERE region = 'SOUTH'
  AND product_category IN ('ELECTRONICS', 'GROCERY')
  AND sales_channel IN ('ONLINE', 'STORE')
GROUP BY sales_channel, product_category
ORDER BY sales_rows DESC;
