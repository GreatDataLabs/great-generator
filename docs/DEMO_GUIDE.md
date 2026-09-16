# Great Generator Demo Guide

**Great Generator** is a developer-first Python library for generating realistic synthetic enterprise datasets for demos, testing, Spark and Pandas workflows, lakehouse pipelines, benchmarking, learning, teaching, dashboards, hackathons, and research.

> Faker gives you fake values. Great Generator gives you a believable enterprise data system.

Great Generator does not just create fake names or fake emails. It creates connected business-style datasets with tables, relationships, realistic values, time behavior, CDC-style records, controlled anomalies, and export support for common analytics formats.

---

## 1. What Great Generator is

Great Generator helps users create realistic synthetic data without relying on private or production data.

It can generate:

- complete industry domain packs such as banking, ecommerce, healthcare, telecom, insurance, logistics, SaaS, and more
- parent-child tables with valid primary keys and foreign keys
- realistic names, emails, phone numbers, addresses, companies, merchants, products, statuses, and account types
- Pandas DataFrames for local notebooks and tests
- Spark DataFrames for Databricks, Fabric, EMR, Synapse, lakehouse demos, and larger workloads
- CSV, JSON, Parquet, and Delta outputs
- CDC-style event records
- intentional data quality problems for testing
- schema-based sample data from user-provided schemas
- custom relational datasets from user-defined tables and relationships

Important privacy note:

> Great Generator creates synthetic data from templates. It does not anonymize, de-identify, or transform real production data.

---

## 2. Who can use Great Generator?

Great Generator is useful for many audiences.

| User | How they can use it |
|---|---|
| Data engineers | Spark pipelines, Delta demos, ETL tests, lakehouse examples |
| Analytics engineers | SQL models, dbt-style examples, dimensional modeling demos |
| BI developers | Dashboard datasets without production data |
| Backend engineers | API/database test data with repeatable shapes |
| QA engineers | Controlled nulls, duplicates, invalid statuses, late records, and broken references |
| ML engineers | Synthetic demo/training datasets with distributions and time behavior |
| Students and learners | Practice SQL, Pandas, Spark, joins, and data engineering concepts |
| Researchers | Reproducible synthetic datasets for experiments and benchmarks |
| Conference speakers | Attractive demo data that looks credible in notebooks and slides |
| Enterprise architects | Multi-table examples for architecture demos and proof-of-concepts |

---

## 3. Platforms and environments

Great Generator is designed to work across common Python and data engineering environments.

| Platform | Supported use |
|---|---|
| Python scripts | Generate local Pandas datasets and files |
| Jupyter / Anaconda notebooks | Interactive demos, teaching, dashboards, exploration |
| Pandas | Local DataFrame generation and CSV/JSON/Parquet writes |
| PySpark | Distributed DataFrame generation |
| Databricks | Spark DataFrames, Parquet, Delta, DBFS/Volumes paths |
| Microsoft Fabric / OneLake | Generate CSV/Parquet data for Lakehouse, notebooks, and Power BI demos |
| AWS Spark clusters | Spark writes to S3 when the cluster is configured |
| Azure Spark clusters | Spark writes to ADLS when the cluster is configured |
| GCP Spark clusters | Spark writes to GCS when the cluster is configured |
| CI pipelines | Repeatable test datasets with seeds |
| Local filesystems | Pandas exports to local folders |

Great Generator does not configure cloud credentials, IAM, storage accounts, mounts, or catalogs. It returns DataFrames and lets your Python/Spark runtime write to the destinations it already supports.

---

## 4. Installation

Install from PyPI:

```bash
pip install great-generator
```

Install optional Spark support:

```bash
pip install great-generator[spark]
```

Install optional Delta support:

```bash
pip install great-generator[delta]
```

Install with a hyphen, import with an underscore:

```python
import great_generator
```

---

## 5. Core public APIs

```python
from great_generator import (
    generate_domain,
    generate_from_schema,
    generate_relational,
    generate_cdc,
    export_data,
    list_domains,
    get_domain_schema,
)
```

| API | Purpose |
|---|---|
| `generate_domain(...)` | Generate a built-in industry domain pack |
| `generate_from_schema(...)` | Generate sample data from a DDL string, Pandas schema, Spark schema, or internal schema |
| `generate_relational(...)` | Generate custom parent-child tables with valid keys |
| `generate_cdc(...)` | Generate CDC-style event records |
| `export_data(...)` | Export generated tables to CSV, JSON, Parquet, or Delta |
| `list_domains()` | Show available domain packs |
| `get_domain_schema(...)` | Inspect a domain schema |

---

## 6. Feature: list available domains

Use this at the start of a demo to show the breadth of built-in examples.

```python
from great_generator import list_domains

print(list_domains())
```

Example domains include:

```text
banking, ecommerce, healthcare, insurance, telecom, automotive,
energy, manufacturing, logistics, media, public_sector,
hospitality, saas
```

---

## 7. Feature: generate a complete domain with Pandas

This is the simplest and most demo-friendly entry point.

```python
from great_generator import generate_domain

banking = generate_domain(
    "banking",
    engine="pandas",
    scale="small",
    realism="realistic",
    seed=42,
)

customers = banking["customers"]
accounts = banking["accounts"]
transactions = banking["transactions"]

print(customers.head())
print(accounts.head())
print(transactions.head())
```

Output is a dictionary of Pandas DataFrames:

```python
{
    "customers": customers_df,
    "accounts": accounts_df,
    "transactions": transactions_df,
    "cards": cards_df,
    "merchants": merchants_df,
    "fraud_events": fraud_events_df,
    "cdc_customer_changes": cdc_customer_changes_df,
}
```

Why this matters in a demo:

- users get a complete system, not one flat table
- joins work immediately
- data looks realistic enough for dashboards and notebooks
- no production data is required

---

## 8. Feature: ecommerce domain example

```python
from great_generator import generate_domain

ecommerce = generate_domain(
    "ecommerce",
    scale="small",
    realism="realistic",
    seed=42,
)

customers = ecommerce["customers"]
products = ecommerce["products"]
orders = ecommerce["orders"]
order_items = ecommerce["order_items"]

print(customers[["customer_id", "customer_name", "email"]].head())
print(products[["product_id", "product_name", "category", "list_price"]].head())
print(orders[["order_id", "customer_id", "order_status", "total_amount"]].head())
```

Example storytelling angle:

> This generates a realistic ecommerce system with customers, products, orders, line items, payments, shipments, and returns. It is useful for order analytics, dashboard demos, fulfillment pipelines, returns analysis, and SQL join practice.

---

## 9. Feature: realistic value generation

Great Generator supports two realism modes:

```python
generate_domain("banking", realism="placeholder")
generate_domain("banking", realism="realistic")
```

`realism="placeholder"` is useful for simple tests and debugging.

`realism="realistic"` generates believable values such as:

- customer names
- first and last names
- emails derived from names
- phone numbers
- addresses
- company names
- merchant names
- product names
- provider names
- account types
- transaction types
- order statuses
- claim statuses

Example:

```python
data = generate_domain("banking", realism="realistic", seed=42)

print(data["customers"][["customer_id", "customer_name", "email"]].head())
```

Example output shape:

```text
customer_id | customer_name     | email
1           | Sheri Wright      | sheri.wright5212@example.com
2           | Jeffrey Allen     | jeffrey.allen4142@example.com
3           | Louis Fuller      | louis.fuller430@example.com
```

Great Generator keeps related descriptive fields aligned. For example, a customer named `Emily Carter` gets an email like `emily.carter247@example.com`, not `john.smith@example.com`.

---

## 10. Feature: relationship-aware generation

Generated data is relationship-safe by default.

For example:

```python
ecommerce = generate_domain("ecommerce", scale="small", seed=42)

orders = ecommerce["orders"]
customers = ecommerce["customers"]
order_items = ecommerce["order_items"]
products = ecommerce["products"]

assert orders["customer_id"].isin(customers["customer_id"]).all()
assert order_items["order_id"].isin(orders["order_id"]).all()
assert order_items["product_id"].isin(products["product_id"]).all()
```

This matters because users can immediately test joins, SQL models, data quality checks, dimensional models, and Spark pipelines.

---

## 11. Feature: generate data from a schema string

Use `generate_from_schema(...)` when you only need a single table from a schema.

```python
from great_generator import generate_from_schema

customers = generate_from_schema(
    "customer_id int, customer_name string, email string, signup_date date, lifetime_value double",
    rows=1000,
    realism="realistic",
    seed=42,
)

print(customers.head())
```

This returns a Pandas DataFrame by default.

Useful for:

- quick sample tables
- unit tests
- notebook demos
- schema-first prototyping
- API payload examples
- teaching data types

---

## 12. Feature: generate data from an empty Pandas DataFrame schema

This is useful when a user already has a Pandas schema but no data.

```python
import pandas as pd
from great_generator import generate_from_schema

empty_customers = pd.DataFrame(
    {
        "customer_id": pd.Series(dtype="int64"),
        "customer_name": pd.Series(dtype="object"),
        "email": pd.Series(dtype="object"),
        "amount": pd.Series(dtype="float64"),
    }
)

customers = generate_from_schema(
    empty_customers,
    rows=100,
    realism="realistic",
    seed=42,
)

print(customers.head())
```

Output stays in Pandas because the input is Pandas.

---

## 13. Feature: generate Spark data from a Spark schema

In a Spark notebook or cluster:

```python
from pyspark.sql import types as T
from great_generator import generate_from_schema

schema = T.StructType(
    [
        T.StructField("customer_id", T.IntegerType(), False),
        T.StructField("customer_name", T.StringType(), True),
        T.StructField("email", T.StringType(), True),
        T.StructField("amount", T.DoubleType(), True),
    ]
)

spark_df = generate_from_schema(
    schema,
    rows=1000,
    spark=spark,
    realism="realistic",
    seed=42,
)

spark_df.show(5, truncate=False)
```

Because a Spark session is provided, the output is a PySpark DataFrame.

---

## 14. Feature: generate a complete domain with Spark

Use Spark when you want distributed DataFrames or lakehouse-style output.

```python
from great_generator import generate_domain

banking = generate_domain(
    "banking",
    engine="spark",
    scale="large",
    realism="realistic",
    spark=spark,
    seed=42,
)

transactions = banking["transactions"]
transactions.printSchema()
transactions.show(5, truncate=False)
```

In many active notebooks, Great Generator can infer the active Spark session. Passing `spark=spark` is still explicit and clear for scripts and demos.

---

## 15. Feature: write Pandas output to local CSV, JSON, and Parquet

Because Pandas output is returned to the user, they can write it however they want.

```python
data = generate_domain("ecommerce", scale="small", realism="realistic", seed=42)

customers = data["customers"]
orders = data["orders"]

customers.to_csv("customers.csv", index=False)
orders.to_json("orders.json", orient="records", lines=True)
orders.to_parquet("orders.parquet", index=False)
```

This is useful for:

- Anaconda/Jupyter demos
- classroom exercises
- local dashboard seed data
- uploading files to BI tools

---

## 16. Feature: convenience export to CSV, JSON, or Parquet

Great Generator can export all tables in a domain at once.

```python
generate_domain(
    "ecommerce",
    engine="pandas",
    scale="small",
    realism="realistic",
    output_path="./synthetic/ecommerce_csv",
    output_format="csv",
)
```

Parquet example:

```python
generate_domain(
    "banking",
    engine="pandas",
    scale="small",
    realism="realistic",
    output_path="./synthetic/banking_parquet",
    output_format="parquet",
)
```

Output layout:

```text
synthetic/
  banking_parquet/
    customers/
    accounts/
    transactions/
    cards/
    merchants/
```

---

## 17. Feature: Spark writes to Parquet and Delta

Spark users often prefer native Spark writes because they can control format, partitioning, catalog registration, options, and cloud paths.

```python
data = generate_domain(
    "banking",
    engine="spark",
    scale="large",
    realism="realistic",
    spark=spark,
)

transactions = data["transactions"]

transactions.write.mode("overwrite").partitionBy("event_date").parquet(
    "s3://my-bucket/demo/banking/transactions"
)
```

Delta example:

```python
transactions.write.format("delta").mode("overwrite").partitionBy("event_date").save(
    "/mnt/demo/banking_delta/transactions"
)
```

Convenience Delta export:

```python
generate_domain(
    "banking",
    engine="spark",
    scale="large",
    realism="realistic",
    spark=spark,
    output_path="/mnt/demo/banking_delta",
    output_format="delta",
    partition_by=["event_date"],
)
```

Delta requires Databricks Runtime or a Spark session configured for Delta Lake.

---

## 18. Feature: cloud and lakehouse paths

For Pandas, write to local paths.

For Spark, the path is handled by the Spark runtime. This means Great Generator can work with storage paths such as:

```text
s3://bucket/path
s3a://bucket/path
abfss://container@account.dfs.core.windows.net/path
gs://bucket/path
/mnt/path
/Volumes/catalog/schema/volume/path
Files/path
```

Examples:

```python
# Databricks / Unity Catalog Volume
transactions.write.format("delta").mode("overwrite").save(
    "/Volumes/demo/synthetic/banking/transactions"
)

# ADLS
transactions.write.mode("overwrite").parquet(
    "abfss://raw@storageaccount.dfs.core.windows.net/demo/banking/transactions"
)

# S3
transactions.write.mode("overwrite").parquet(
    "s3://my-demo-bucket/banking/transactions"
)

# GCS
transactions.write.mode("overwrite").parquet(
    "gs://my-demo-bucket/banking/transactions"
)
```

The cluster must already have the correct credentials and filesystem connectors.

---

## 19. Feature: CDC simulation

CDC means Change Data Capture. It is useful for testing incremental pipelines, merge logic, streaming-style ingestion, and lakehouse table updates.

```python
from great_generator import generate_cdc

cdc = generate_cdc(
    "banking",
    table="customers",
    rows=10000,
    operations=["insert", "update", "delete"],
    late_arrival_rate=0.02,
    duplicate_rate=0.005,
    seed=42,
)

print(cdc.head())
print(cdc["operation"].value_counts())
```

CDC output includes:

- operation type
- before payload
- after payload
- event timestamp
- ingestion timestamp
- sequence number
- source system
- late-arriving flag
- duplicate flag

Demo idea:

> Show how CDC data can feed a bronze table, then use sequence numbers and timestamps to build silver current-state tables.

---

## 20. Feature: anomaly injection

By default, generated data is clean and relationship-safe. Anomalies are added only when explicitly requested.

```python
dirty = generate_domain(
    "ecommerce",
    scale="small",
    realism="realistic",
    seed=42,
    anomalies={
        "null_rate": 0.02,
        "duplicate_rate": 0.01,
        "orphan_fk_rate": 0.001,
        "late_arrival_rate": 0.02,
        "outlier_rate": 0.005,
        "invalid_status_rate": 0.01,
    },
)
```

Useful for:

- data quality tool demos
- pipeline resilience tests
- invalid value handling
- deduplication tests
- late-arriving event tests
- broken foreign-key validation

---

## 21. Feature: custom relational data generation

Use `generate_relational(...)` when users provide their own tables and relationships.

```python
from great_generator import generate_relational

retail = generate_relational(
    tables={
        "customers": {
            "schema": "customer_id int primary key, customer_name string, email string",
            "rows": 1000,
        },
        "orders": {
            "schema": "order_id int primary key, customer_id int references customers.customer_id, order_total double",
            "rows": 10000,
        },
        "payments": {
            "schema": "payment_id int primary key, order_id int references orders.order_id, amount double, payment_status string",
            "rows": 10000,
        },
    },
    engine="pandas",
    realism="realistic",
    seed=42,
)

customers = retail["customers"]
orders = retail["orders"]
payments = retail["payments"]

assert orders["customer_id"].isin(customers["customer_id"]).all()
assert payments["order_id"].isin(orders["order_id"]).all()
```

This is powerful for demos because users can bring their own schema shape without writing a full domain pack.

---

## 22. Feature: scale profiles

Scale profiles give simple dataset sizes without requiring every table count.

```python
generate_domain("ecommerce", scale="tiny")
generate_domain("ecommerce", scale="small")
generate_domain("ecommerce", scale="medium")
generate_domain("ecommerce", scale="large")
```

Use cases:

| Scale | Best for |
|---|---|
| `tiny` | README examples, unit tests, quick notebook checks |
| `small` | local development and demos |
| `medium` | richer notebooks and dashboards |
| `large` | Spark and performance testing |

---

## 23. Feature: custom row counts

Override row counts when you need a specific shape.

```python
data = generate_domain(
    "ecommerce",
    rows={
        "customers": 100000,
        "products": 10000,
        "orders": 1000000,
        "order_items": 3000000,
    },
    realism="realistic",
    seed=42,
)
```

This is useful for benchmark demos and performance testing.

---

## 24. Feature: reproducibility with seeds

Seeds are optional. Use them when you want repeatable output.

```python
data1 = generate_domain("banking", scale="tiny", realism="realistic", seed=42)
data2 = generate_domain("banking", scale="tiny", realism="realistic", seed=42)

assert data1["customers"].equals(data2["customers"])
```

Different seeds produce different synthetic values.

```python
data3 = generate_domain("banking", scale="tiny", realism="realistic", seed=2026)
```

Good demo explanation:

> Seed is not required, but it is useful when you want the same workshop, test, or research example to produce the same data every time.

---

## 25. Feature: inspect domain schema metadata

```python
from great_generator import get_domain_schema

schema = get_domain_schema("banking")

print(schema.name)
print(schema.description)
print(schema.as_dict())
```

Use this to explain what tables, columns, and relationships exist before generating the data.

---

## 26. Suggested demo flow

A strong 10-minute demo can follow this sequence:

1. Install and import Great Generator.
2. Run `list_domains()`.
3. Generate `banking` with Pandas.
4. Show realistic customers and transactions.
5. Prove relationships with a join or `isin` check.
6. Generate ecommerce and show products/orders/order_items.
7. Generate from a custom schema.
8. Generate custom relational customers/orders/payments.
9. Inject anomalies and explain data quality testing.
10. Show Spark generation and write to Parquet or Delta.
11. Show the PyPI page and Wiki for deeper docs.

---

## 27. Notebook-friendly demo script

```python
from great_generator import generate_domain, generate_from_schema, generate_cdc, list_domains

print("Available domains:")
print(list_domains())

print("\nBanking domain:")
banking = generate_domain("banking", scale="tiny", realism="realistic", seed=42)
print(banking["customers"][["customer_id", "customer_name", "email"]].head())
print(banking["transactions"].head())

print("\nEcommerce domain:")
ecommerce = generate_domain("ecommerce", scale="tiny", realism="realistic", seed=42)
print(ecommerce["products"][["product_id", "product_name", "category", "list_price"]].head())
print(ecommerce["orders"][["order_id", "customer_id", "order_status", "total_amount"]].head())

print("\nSchema generation:")
sample = generate_from_schema(
    "id int, customer_name string, email string, amount double",
    rows=5,
    realism="realistic",
    seed=42,
)
print(sample)

print("\nCDC sample:")
cdc = generate_cdc("banking", table="customers", rows=10, seed=42)
print(cdc.head())
```

---

## 28. Common questions during demos

### Is Great Generator a data anonymization tool?

No. It creates synthetic data from templates. It does not anonymize or transform real production data.

### Is this just Faker?

No. Faker generates individual values. Great Generator creates connected domain datasets with keys, relationships, realistic business values, CDC, anomalies, Pandas/Spark support, and exports.

### Can it work in Databricks?

Yes. Use the Spark engine and write Spark DataFrames to Parquet or Delta paths supported by your Databricks workspace.

### Can it work in Microsoft Fabric?

Yes. Generate Pandas or Spark data, write CSV/Parquet, and use those files in a Fabric Lakehouse, notebook, semantic model, or Power BI demo.

### Does seed have to be used?

No. Seed is optional. It is recommended for repeatable tests, demos, and research examples.

### Can users write to databases?

Yes. Great Generator returns DataFrames. Users can write using native Pandas, Spark, SQLAlchemy, JDBC, or platform-specific APIs.

---

## 29. Why this library is valuable

Great Generator is valuable because realistic data work usually needs more than fake values.

A realistic demo needs:

- customers with orders
- products with prices
- accounts with transactions
- patients with encounters and claims
- payments, shipments, invoices, statuses, timestamps, and event dates
- valid joins
- repeatability
- optional messy data
- local and Spark-scale outputs

That is the difference:

> Faker gives you fake values. Great Generator gives you a believable enterprise data system.

---

## 30. Useful links

- PyPI: https://pypi.org/project/great-generator/
- GitHub: https://github.com/GreatDataLabs/great-generator
- Wiki: https://github.com/GreatDataLabs/great-generator/wiki
- Release notes: https://github.com/GreatDataLabs/great-generator/releases
