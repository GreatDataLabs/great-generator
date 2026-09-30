# Platform examples

Great Generator includes practical examples for common data engineering and analytics environments. The examples show how to generate synthetic non-production datasets, return DataFrames, and write those DataFrames using the user's runtime.

Great Generator does not create platform resources, configure credentials, manage secrets, or write to production systems by default.

## Example folders

| Folder | Platform | What it shows | Credentials required? |
|---|---|---|---|
| `examples/pandas/` | Local Python, Anaconda, Jupyter, VS Code | Pandas generation, JSON Schema, dbt metadata, data dictionaries, relational data, query-aware generation, CDC, anomalies | No |
| `examples/databricks/` | Databricks, Spark, Delta Lake, Unity Catalog | Generate DataFrames, convert to Spark, write Delta tables and paths | User-managed |
| `examples/fabric/` | Microsoft Fabric Lakehouse | Generate data in Fabric Spark and write Lakehouse tables/files | User-managed |
| `examples/snowflake/` | Snowflake | Generate Parquet files and load with stage/COPY templates | User-managed |
| `examples/cloud_storage/` | S3, ADLS Gen2, GCS | Write synthetic data to cloud object storage with native writers or optional helper | User-managed |

## Pandas and local development

Use Pandas examples when you want to test locally or demo in a notebook:

```python
from great_generator import generate_from_schema

df = generate_from_schema("customer_id int, email string, signup_date date", rows=1000)
df.to_parquet("output/customers.parquet", index=False)
```

## Databricks and Delta Lake

Databricks examples follow the DataFrame-first pattern:

```python
from great_generator import generate_from_schema

pdf = generate_from_schema("customer_id int, email string", rows=100000)
sdf = spark.createDataFrame(pdf)
sdf.write.format("delta").mode("overwrite").saveAsTable("default.synthetic_customers")
```

For Unity Catalog, replace table and volume placeholders with catalog, schema, table, and volume names configured by your workspace administrators.

## Microsoft Fabric

Fabric examples use Fabric Spark notebooks and Lakehouse tables:

```python
pdf = generate_from_schema("customer_id int, email string", rows=100000)
sdf = spark.createDataFrame(pdf)
sdf.write.mode("overwrite").format("delta").saveAsTable("synthetic_customers")
```

## Snowflake

Snowflake examples prefer file-based loading. Generate Parquet, stage it using your own storage integration, then run `COPY INTO`.

```sql
COPY INTO target_schema.synthetic_customers
FROM @great_generator_stage/customers/
FILE_FORMAT = (TYPE = PARQUET)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE;
```

## Cloud storage

Cloud examples include S3, ADLS Gen2, and GCS path patterns. Credentials and permissions must be configured in the runtime environment.

## Limitations

- Examples are synthetic and non-production.
- Examples do not configure IAM, service principals, secrets, storage integrations, or workspace grants.
- Benchmark examples are repeatable templates, not universal performance claims.
- Large row counts depend on the user's memory, cluster size, warehouse size, storage layout, and runtime configuration.
