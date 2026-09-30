-- Snowflake stage and COPY INTO example for Great Generator outputs.
-- Configure your own database, schema, warehouse, stage, storage integration, and path.
-- Do not place credentials in SQL files.

CREATE OR REPLACE FILE FORMAT great_generator_parquet_format
  TYPE = PARQUET;

-- Example only. Configure your own stage, storage integration, and path.
-- CREATE OR REPLACE STAGE great_generator_stage
--   URL = 's3://your-bucket/synthetic/'
--   STORAGE_INTEGRATION = your_storage_integration
--   FILE_FORMAT = great_generator_parquet_format;

CREATE TABLE IF NOT EXISTS target_schema.synthetic_customers (
  customer_id NUMBER,
  customer_name STRING,
  email STRING,
  signup_date DATE,
  account_status STRING,
  balance NUMBER(12,2)
);

COPY INTO target_schema.synthetic_customers
FROM @great_generator_stage/customers/
FILE_FORMAT = (TYPE = PARQUET)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE;
