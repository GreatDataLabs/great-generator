# great-generator

Generate realistic synthetic data from schemas, SQL DDL, relationships, and generation plans for data engineering, testing, analytics, Spark, and lower environments.

## Why great-generator?

Data teams often know their schema but cannot copy production records into development, QA, SIT, UAT, sandbox, demo, or performance environments. Great Generator creates fake, non-production data from table-like schemas so teams can test pipelines, applications, dashboards, and data models without depending on production extracts.

Great Generator creates synthetic data. It does not anonymize, mask, de-identify, or transform production records.

## Main Feature: `generate_from_schema`

```python
from great_generator import generate_from_schema

schema = {
    "customer_id": "string",
    "customer_name": "string",
    "age": "int",
    "email": "string",
    "balance": "float",
    "created_at": "datetime",
    "account_status": "string",
}

df = generate_from_schema(schema, rows=1000)
```

Semantic field inference recognizes name-like fields, IDs, contact details, ages, dates, amounts, quantities, statuses, and common cross-field relationships.

## SQL DDL Contracts

```python
from great_generator import generate_from_schema, parse_ddl

ddl = """
CREATE TABLE sales.customers (
    customer_id BIGINT PRIMARY KEY,
    customer_name STRING NOT NULL,
    email VARCHAR(120) UNIQUE,
    signup_date DATE,
    balance DECIMAL(12,2)
)
"""

contract = parse_ddl(ddl, dialect="databricks")
df = generate_from_schema(contract, rows=1000)
```

`parse_ddl(...)` supports the documented ANSI, Spark, and Databricks `CREATE TABLE` subset. It preserves canonical contract metadata, parser diagnostics, stable fingerprints, column order, normalized types, keys, constraints, comments, defaults, and selected storage metadata where supported.

## Query-Aware Generation

```python
df = generate_from_schema(
    schema,
    rows=10000,
    required_values={"account_status": ["Active", "Pending"]},
    partition_by={"event_date": {"start": "2026-01-01", "end": "2026-01-31"}},
    target_selectivity={"account_status": {"Active": 0.70}},
)
```

Query-aware generation helps synthetic data contain expected filter values, partition dates, selectivity targets, and join paths. It does not guarantee identical production performance because runtime depends on storage layout, table statistics, clustering, caching, concurrency, warehouse size, and engine configuration.

## Optional Advisor Layer

Advisors provide design-time schema understanding, column tagging, and realism review. They produce inspectable JSON artifacts such as `GenerationPlan` and `ColumnTags`. Advisors do not generate row data, and `advisor="none"` is the offline default.

## Generate Related Tables

```python
from great_generator import generate_relational

data = generate_relational(
    tables={
        "customers": {
            "schema": "customer_id int primary key, customer_name string",
            "rows": 1000,
        },
        "orders": {
            "schema": "order_id int primary key, customer_id int references customers.customer_id, order_amount double",
            "rows": 5000,
        },
    }
)

customers_df = data["customers"]
orders_df = data["orders"]
```

Use `generate_relational` for connected tables with valid keys. Use prebuilt domains when you need ready-made demonstration data.

## Installation

```bash
pip install great-generator
pip install "great-generator[spark]"
pip install "great-generator[delta]"
pip install "great-generator[ai]"
pip install "great-generator[anthropic]"
pip install "great-generator[ollama]"
```

Install with a hyphen. Import with an underscore:

```python
import great_generator
```

## Supported Schema Inputs

- plain Python `{column: dtype}` mappings
- Pandas dtype mappings and DataFrames
- compact DDL strings such as `"id int, name string"`
- documented SQL `CREATE TABLE` DDL through `parse_ddl(...)`
- JSON Schema through `generate_from_json_schema(...)`
- dbt `schema.yml` through `generate_from_dbt_schema(...)`
- dbt `manifest.json` through `generate_from_dbt_manifest(...)`
- CSV, YAML, and JSON data dictionaries through `generate_from_data_dictionary(...)`
- PySpark `StructType` and DataFrames
- Great Generator `TableSchema` and `DomainSchema` objects

SQLAlchemy, Pydantic, dataclass, OpenAPI, Avro, and column-list inputs remain roadmap items.

## Write Output Anywhere Your DataFrame Supports

```python
df.to_csv("customers.csv", index=False)
df.to_json("customers.json", orient="records", lines=True)
df.to_parquet("customers.parquet", index=False)
```

Spark results support normal Spark writers for Parquet, Delta, Databricks tables, Fabric Lakehouse, S3, ADLS, GCS, DBFS, and catalog workflows when the runtime is configured.

## Real-World Uses

- lower-environment test data
- ETL and ELT validation
- QA, SIT, and UAT datasets
- lakehouse and warehouse testing
- API and application integration tests
- BI dashboard development
- data quality and edge-case testing
- prototypes, demos, research, and learning

## Prebuilt Domains and Advanced APIs

`generate_domain` provides ready-made related datasets for ecommerce, banking, healthcare, insurance, telecom, automotive, energy, manufacturing, logistics, media, public sector, hospitality, and SaaS.

Additional APIs support CDC records, controlled anomalies, SCD2 history, dimensional models, Data Vault models, recipes, CLI workflows, and CSV, JSON, Parquet, and Delta convenience exports.

## Disclaimer

Great Generator creates synthetic data. It does not anonymize or transform production data and does not guarantee privacy, compliance, or statistical equivalence. Follow your organization's governance, privacy, security, and compliance requirements.

## Links

- [Documentation](https://ravikiranpagidi.github.io/great-generator/)
- [GitHub](https://github.com/ravikiranpagidi/great-generator)
- [Wiki](https://github.com/ravikiranpagidi/great-generator/wiki)
- [Issues](https://github.com/ravikiranpagidi/great-generator/issues)
