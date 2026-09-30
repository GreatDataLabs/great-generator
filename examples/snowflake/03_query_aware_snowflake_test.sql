-- Query-aware Snowflake test examples.
-- Run these after loading synthetic_query_test through your own stage/COPY workflow.

SELECT business_date, product_type, COUNT(*) AS rows
FROM target_schema.synthetic_query_test
WHERE business_date BETWEEN '2026-01-01' AND '2026-01-03'
  AND region = 'SOUTH'
  AND product_type IN ('CHECKING', 'SAVINGS')
GROUP BY business_date, product_type
ORDER BY business_date, product_type;

SELECT member_status, region, AVG(balance) AS avg_balance, COUNT(*) AS rows
FROM target_schema.synthetic_query_test
GROUP BY member_status, region
ORDER BY rows DESC;

-- These queries are templates for your environment. They are not platform performance claims.
