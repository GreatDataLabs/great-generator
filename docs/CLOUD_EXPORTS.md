# Cloud exports

Great Generator is DataFrame-first. Most users can generate synthetic data, receive a Pandas or Spark DataFrame, and write it using the native APIs of their runtime.

## Native writes

### Pandas local files

```python
from great_generator import generate_from_schema

df = generate_from_schema("customer_id int, email string", rows=1000)
df.to_csv("output/customers.csv", index=False)
df.to_parquet("output/customers.parquet", index=False)
```

### Spark, Databricks, Fabric, Synapse, EMR, or other Spark runtimes

```python
pdf = generate_from_schema("customer_id int, email string", rows=100000)
sdf = spark.createDataFrame(pdf)
sdf.write.mode("overwrite").parquet("s3://your-bucket/great-generator/customers/")
```

## Optional `export_dataset` helper

`export_dataset` is a convenience helper for one DataFrame or a mapping of table-name DataFrames.

```python
from great_generator import export_dataset, generate_from_schema

df = generate_from_schema("customer_id int, email string", rows=1000)
export_dataset(df, "output/customers", format="parquet")
```

Existing outputs are rejected by default. Use `overwrite=True` or `mode="overwrite"` only when replacing files is intentional.

```python
export_dataset(df, "output/customers", format="parquet", overwrite=True)
```

Supported helper formats:

| Format | Notes |
|---|---|
| `csv` | Single CSV file for Pandas; Spark writes a folder. |
| `jsonl` | Newline-delimited JSON for Pandas; Spark JSON folder for Spark. |
| `parquet` | Parquet file for Pandas; Parquet folder for Spark. |

## Optional cloud extra

Cloud URL support for Pandas helper writes uses optional fsspec-backed dependencies:

```bash
pip install "great-generator[cloud]"
```

Supported path families depend on installed filesystem packages and runtime credentials:

| Path | Optional filesystem package | Example |
|---|---|---|
| S3 | `s3fs` | `s3://your-bucket/great-generator/customers` |
| ADLS Gen2 | `adlfs` | `abfss://container@account.dfs.core.windows.net/great-generator/customers` |
| GCS | `gcsfs` | `gs://your-bucket/great-generator/customers` |

## Credential guidance

Great Generator does not create cloud resources, configure IAM, create service principals, manage secrets, or grant storage permissions.

Configure credentials using your platform's standard method:

- Databricks instance profiles, Unity Catalog external locations, or workspace secrets
- Azure managed identity, service principal, or Fabric workspace configuration
- Google service accounts or workload identity
- Local environment variables or cloud SDK profiles for development

Do not put credentials in notebooks, SQL files, repository files, or generated examples.
