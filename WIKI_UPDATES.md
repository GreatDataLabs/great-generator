# Wiki Updates for Schema-Source Ingestion and Query-Aware Generation

Use this copy to update the Great Generator GitHub Wiki after merging the schema-source ingestion changes.

---

## Home.md

# Great Generator

Great Generator is a schema-first synthetic data generator for data engineering, testing, analytics, SQL contracts, relational data, query-aware datasets, Spark/lakehouse workflows, and deterministic AI-assisted planning.

## Key capabilities

- **Schema-first generation**: Generate synthetic data from practical schema definitions.
- **SQL DDL support**: Parse documented `CREATE TABLE` DDL and generate data from database-style contracts.
- **JSON Schema support**: Generate data from API-style JSON Schema contracts.
- **dbt integration**: Generate synthetic data from dbt `schema.yml` and `manifest.json` metadata.
- **Data dictionary support**: Generate data from CSV, YAML, or JSON data dictionaries.
- **Query-aware generation**: Include required values, partition dates, and join paths needed by SQL tests.
- **Relational generation**: Generate connected parent-child tables with primary-key and foreign-key consistency.
- **Spark and lakehouse workflows**: Return Spark DataFrames where supported and write with native Spark APIs.
- **Optional AI advisor layer**: Review and plan generation semantics before producing rows.
- **Optional MCP server**: Let MCP-compatible assistants call selected local Great Generator tools.

---

## Getting-Started.md

# Getting Started

Install:

```bash
pip install great-generator
```

Import with an underscore:

```python
from great_generator import generate_from_schema

schema = "customer_id int, customer_name string, email string, created_at datetime"
df = generate_from_schema(schema, rows=1000)
```

Optional extras:

```bash
pip install "great-generator[spark]"
pip install "great-generator[delta]"
pip install "great-generator[dbt]"
pip install "great-generator[schema-ingest]"
pip install "great-generator[ai]"
pip install "great-generator[mcp]"
```

Great Generator creates synthetic data. It does not anonymize, mask, de-identify, or transform production records.

---

## Schema-Inputs.md

# Schema Inputs

| Input type | Supported | Function |
|---|---:|---|
| Python dict | Yes | `generate_from_schema` |
| Compact DDL string | Yes | `generate_from_schema` |
| Full SQL CREATE TABLE DDL | Yes | `parse_ddl`, `generate_from_schema` |
| Pandas DataFrame | Yes | `generate_from_schema` |
| PySpark StructType | Yes | `generate_from_schema` |
| JSON Schema | Yes | `generate_from_json_schema` |
| dbt schema.yml | Yes | `generate_from_dbt_schema` |
| dbt manifest.json | Yes | `generate_from_dbt_manifest` |
| Data dictionary CSV/YAML/JSON | Yes | `generate_from_data_dictionary` |
| Pydantic model | Planned | TBD |
| SQLAlchemy model | Planned | TBD |
| OpenAPI schema | Planned | TBD |

All schema inputs are normalized into the existing generation path. No second generation engine is introduced.

---

## JSON-Schema.md

# JSON Schema

```python
from great_generator import generate_from_json_schema

json_schema = {
    "type": "object",
    "required": ["customer_id", "email"],
    "properties": {
        "customer_id": {"type": "integer"},
        "email": {"type": "string", "format": "email"},
        "status": {"type": "string", "enum": ["ACTIVE", "INACTIVE", "PENDING"]},
        "balance": {"type": "number", "minimum": 0, "maximum": 10000},
    },
}

df = generate_from_json_schema(json_schema, rows=1000)
```

Supported v1 subset: top-level object, properties, required fields, string, integer, number, boolean, basic arrays, date/date-time/email formats, enum, minimum, maximum, description, and default metadata.

Unsupported or partial features include oneOf, anyOf, allOf, not, patternProperties, external refs, recursive schemas, and deep nested object graphs.

---

## dbt-Integration.md

# dbt Integration

```python
from great_generator import generate_from_dbt_schema, generate_from_dbt_manifest

df = generate_from_dbt_schema("models/schema.yml", model_name="customers", rows=1000)
from_manifest = generate_from_dbt_manifest("target/manifest.json", model_name="customers", rows=1000)
```

Install YAML support for `schema.yml`:

```bash
pip install "great-generator[dbt]"
```

Mapped metadata: column name, data type, description, not_null, unique, accepted_values, and relationship hints where possible.

---

## Data-Dictionary.md

# Data Dictionary

```python
from great_generator import generate_from_data_dictionary, load_data_dictionary

schema = load_data_dictionary("data_dictionary.csv")
df = generate_from_data_dictionary("data_dictionary.csv", rows=1000)
```

Supported file types: CSV, YAML, JSON.

Recommended fields: `column_name`, `data_type`, `nullable`, `description`, `allowed_values`, `min`, `max`, `unique`, `primary_key`, `foreign_key`, and `pii_class`.

`pii_class` is metadata only and does not imply compliance classification or anonymization.

---

## Query-Aware-Generation.md

# Query-Aware Generation

Query-aware generation helps synthetic data match expected query values, partition dates, and join paths.

```python
from great_generator import generate_from_schema, validate_query_coverage

schema = """
member_id string,
business_date date,
region string,
product_type string,
member_status string,
interaction_count int,
balance double
"""

required_values = {
    "region": ["SOUTH"],
    "product_type": ["CHECKING", "SAVINGS"],
    "member_status": ["ACTIVE"],
}

partition_by = {
    "column": "business_date",
    "values": ["2026-01-01", "2026-01-02", "2026-01-03"],
    "distribution": "balanced",
}

df = generate_from_schema(schema, rows=100000, required_values=required_values, partition_by=partition_by)
report = validate_query_coverage(data=df, required_values=required_values, partition_by=partition_by)
```

Query-aware generation does not guarantee identical production performance because file layout, statistics, clustering, caching, concurrency, warehouse size, and query engine configuration also affect runtime.

---

## FAQ.md

# FAQ

## Does Great Generator anonymize production data?

No. Great Generator creates synthetic records from schema contracts and generation rules. It does not anonymize, mask, de-identify, or transform production records.

## Does JSON Schema ingestion support every JSON Schema feature?

No. The first implementation supports a practical flat-record subset. Complex composition keywords, external references, recursive schemas, and deep nested object graphs are not fully supported.

## Does dbt integration run dbt?

No. It reads dbt metadata files such as `schema.yml` and `target/manifest.json`. It does not run dbt commands or connect to your warehouse.

## Can I write the output anywhere?

The APIs return DataFrames. You can write them using native Pandas or Spark writers to CSV, JSON, Parquet, Delta, cloud storage, or databases according to your own runtime, connectors, permissions, and credentials.

---

# Platform adoption update

Copy-paste-ready wiki updates for platform examples, cloud exports, and the synthetic benchmark harness.

## Home.md additions

Add these feature bullets:

- **Platform examples**: Ready-to-run examples for Pandas, Databricks, Microsoft Fabric, Snowflake, and cloud storage.
- **Cloud export examples**: Write generated synthetic data to local files, S3, ADLS Gen2, and Google Cloud Storage using user-managed credentials.
- **Synthetic benchmark harness**: Generate repeatable synthetic datasets and SQL query templates for platform testing in your own environment.

Add this safety note:

> Great Generator creates synthetic non-production data. It does not anonymize, mask, de-identify, or transform production records.

## Getting-Started.md additions

```python
from great_generator import generate_from_schema, export_dataset

df = generate_from_schema("customer_id int, email string", rows=1000)
export_dataset(df, "output/customers", format="parquet")
```

Existing outputs are rejected by default. Use `overwrite=True` only when replacement is intentional.

## Platform-Examples.md

Great Generator includes platform examples for:

- Pandas/local notebooks: `examples/pandas/`
- Databricks and Delta Lake: `examples/databricks/`
- Microsoft Fabric Lakehouse: `examples/fabric/`
- Snowflake stage/COPY workflows: `examples/snowflake/`
- Cloud storage paths: `examples/cloud_storage/`

The examples show DataFrame-first workflows. Users generate synthetic data, receive Pandas or Spark DataFrames, and then write those DataFrames using their runtime's native APIs.

## Cloud-Exports.md

Great Generator supports native DataFrame writes and an optional helper:

```bash
pip install "great-generator[cloud]"
```

```python
from great_generator import export_dataset

export_dataset(df, "s3://your-bucket/great-generator/customers", format="parquet", overwrite=True)
```

Great Generator does not create cloud resources, configure IAM, create service principals, manage secrets, or grant storage permissions.

## Benchmark-Harness.md

The benchmark harness is under `benchmarks/`.

Implemented dataset:

- `retail_star_schema`
- Tables: `dim_customer`, `dim_product`, `dim_store`, `dim_date`, `fact_sales`
- Query templates: partition filter, join aggregation, selectivity filter, monthly rollup, large group-by

Required limitation wording:

> These benchmark examples are designed to help users generate repeatable synthetic datasets and query templates for their own environments. They are not universal performance claims. Results depend on warehouse size, cluster configuration, storage layout, file format, statistics, clustering, caching, concurrency, and query engine settings.

## Databricks-Examples.md

Use `examples/databricks/` for Delta, partitioned writes, and Unity Catalog Volume path examples. Replace placeholders with your workspace's governed catalog, schema, volume, table, and path names.

## Unity-Catalog-Generation.md

Great Generator can use a fully qualified Unity Catalog table as a metadata source. It reads only the schema, tags, and constraints the caller is permitted to see, converts them into existing Great Generator contracts, and generates synthetic Pandas or Spark DataFrames without reading source records.

```python
from great_generator import generate_relational_from_unity_catalog

datasets, report = generate_relational_from_unity_catalog(
    "retail.sales.fact_orders",
    include_related=True,
    related_direction="parents",
    rows={
        "dim_customer": 10_000,
        "dim_product": 1_000,
        "fact_orders": 100_000,
    },
    output="spark",
    spark=spark,
    return_report=True,
)
```

Supported relationship modes:

- `declared`: use accessible Unity Catalog PK/FK metadata;
- `inferred`: add clearly labeled conservative suggestions with confidence and evidence;
- `explicit`: use reviewed mappings when catalog constraints are absent.

The adapter validates simple and composite key relationships. Cyclic and self-referencing graphs fail clearly because staged cycle resolution is not implemented yet.

See `docs/DATABRICKS_UNITY_CATALOG.md`, `docs/UC_RELATIONAL_GENERATION.md`, and `examples/databricks/unity_catalog/`.

## Unity-Catalog-Notebook-Builder.md

`generate_uc_ingestion_code(...)` creates a reviewable Databricks notebook plus generation configuration, relationships, schema snapshot, validation placeholder, and generation manifest. Notebook creation never executes writes. The generated write cell defaults to `ENABLE_WRITES = False`, requires a separate synthetic target namespace, and uses `errorifexists`.

## Unity-Catalog-Snapshots.md

```python
from great_generator import compare_uc_schema_snapshots, inspect_unity_catalog_table

snapshot = inspect_unity_catalog_table("retail.sales.fact_orders", spark=spark)
snapshot.save("fact_orders_schema.json")

diff = compare_uc_schema_snapshots(
    "fact_orders_schema.json",
    "fact_orders_schema_latest.json",
)
print(diff.to_text())
```

Snapshots contain normalized metadata, not records or credentials. Comparison reports schema drift but never migrates source tables.

## Fabric-Examples.md

Use `examples/fabric/` for Fabric Spark notebooks, Lakehouse table writes, OneLake Files writes, and query-aware test data.

## Snowflake-Examples.md

Use `examples/snowflake/` for a file-based load flow:

1. Generate synthetic Parquet.
2. Stage files through user-managed cloud storage or an internal Snowflake stage.
3. Run `COPY INTO` using the provided SQL templates.

No credentials are included in the examples.

## FAQ.md additions

### Does Great Generator configure cloud credentials?

No. Great Generator does not manage secrets, IAM, service principals, Unity Catalog grants, Snowflake storage integrations, or cloud permissions.

### Does Unity Catalog generation read production data?

No. Normal discovery reads permitted metadata from Unity Catalog information-schema views. Great Generator generates new synthetic records through its existing engines.

### Are Unity Catalog constraints always complete?

No. Metadata is permission-filtered and constraints may not be declared. Use explicit relationships when needed, and review inferred suggestions before relying on them.

### Are benchmark examples platform rankings?

No. They are repeatable synthetic workloads users can run in their own environments. Results depend on configuration, file layout, runtime settings, statistics, cache state, concurrency, and compute size.


---

## Hugging Face Integration wiki updates

Copy these sections into the GitHub Wiki when publishing the next documentation refresh.

### Home.md additions

Add this feature bullet:

- **Hugging Face integration**: Convert generated data to Hugging Face Datasets, generate dataset cards, and optionally use local Transformers models for advisor planning.

### Hugging-Face-Integration.md

# Hugging Face Integration

Great Generator can optionally integrate with the Hugging Face ecosystem. The base package does not require Hugging Face dependencies.

Install:

```bash
pip install "great-generator[hf]"
```

Convert generated pandas data to a Hugging Face Dataset:

```python
from great_generator import generate_from_schema, to_hf_dataset

df = generate_from_schema("customer_id int, email string", rows=1000, seed=42)
dataset = to_hf_dataset(df)
```

Convert related generated tables to a DatasetDict:

```python
from great_generator import generate_relational, to_hf_dataset_dict

data = generate_relational(
    tables={
        "customers": "customer_id int, email string",
        "orders": "order_id int, customer_id int, order_total double",
    },
    relationships=["customers.customer_id -> orders.customer_id"],
    rows={"customers": 100, "orders": 500},
    seed=42,
)

dataset_dict = to_hf_dataset_dict(data)
```

Generate a dataset card:

```python
from great_generator import generate_hf_dataset_card

card = generate_hf_dataset_card(
    dataset_name="synthetic-retail-star-schema",
    row_counts={"dim_customer": 10000, "fact_sales": 1000000},
    seed=42,
)
```

Great Generator does not upload to the Hugging Face Hub automatically. Review generated data and dataset cards before publishing anything manually.

### Transformers-Advisor.md

# Transformers Advisor

The optional Transformers advisor can use a local or cached Hugging Face Transformers model for design-time planning.

Install:

```bash
pip install "great-generator[transformers]"
```

Example:

```python
from great_generator import generate_from_schema, infer_generation_plan

schema = "customer_id int, email string"
plan = infer_generation_plan(schema, advisor="transformers:google/flan-t5-small")
df = generate_from_schema(schema, rows=1000, plan=plan, seed=42)
```

TransformersAdvisor helps at design time. It does not generate row data. Generation remains deterministic from the saved plan and seed.

By default, the advisor loads local files only. Use a local model path or pre-download/cache the model before running it.

### FAQ.md additions

#### Does Great Generator require Hugging Face?

No. Hugging Face integrations are optional.

#### Does Transformers generate the synthetic rows?

No. TransformersAdvisor can help create plans, tags, or reports, but row generation remains deterministic inside Great Generator.

#### Can I publish generated datasets to Hugging Face Hub?

Yes, but v1 generates local dataset/card artifacts and leaves publishing to the user through Hugging Face's standard tools. Great Generator does not upload automatically.

#### Is Great Generator part of Hugging Face Transformers?

No. It is an independent open-source project with optional Hugging Face ecosystem integrations.

---

# Contract-to-Test Wiki Updates

The sections below are copy-ready for the live GitHub Wiki. They describe the implemented Phase 1 subset and label later phases honestly.

## Home.md addition

- **Contract-to-Test generation**: Parse a documented SQL `SELECT` subset and create deterministic witness rows for predicates, joins, boundaries, and SQL NULL behavior, with explicit coverage reports.

## Contract-to-Test.md

# Contract-to-Test

Great Generator can compile a normalized schema contract and supported SQL workload into synthetic test datasets:

```python
from great_generator.testing import compile_test_dataset

result = compile_test_dataset(
    schema={
        "customers": {
            "customer_id": {"type": "integer", "primary_key": True},
            "region": {"type": "string", "allowed_values": ["EAST", "WEST"]},
        },
        "orders": {
            "order_id": {"type": "integer", "primary_key": True},
            "customer_id": {"type": "integer", "nullable": False},
            "status": {"type": "string", "allowed_values": ["OPEN", "COMPLETED"]},
            "amount": {"type": "number", "minimum": 0},
        },
    },
    relationships=["customers.customer_id -> orders.customer_id"],
    queries="""
        SELECT o.order_id
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE c.region = 'EAST'
          AND o.status = 'COMPLETED'
          AND o.amount >= 100
    """,
    rows={"customers": 20, "orders": 40},
    coverage=["predicates", "joins", "boundaries", "null_handling"],
    seed=42,
)

assert result.validate()["passed"]
coverage = result.coverage_report()
result.generate_report(format="html", output="reports/coverage.html")
```

Phase 1 uses the existing Pandas generation path. It does not claim arbitrary SQL compatibility, complete query-result oracles, native Spark witness generation, or generic cyclic relationship support.

## SQL-Workload-Analysis.md

# SQL Workload Analysis

`parse_sql_workload(...)` parses SQL without executing it. The implemented subset covers top-level `SELECT`, table aliases, qualified columns, inner and left equality joins, comparison operators, `IN`, `NOT IN`, `BETWEEN`, NULL predicates, basic `GROUP BY`, common aggregates, and date literals. Unsupported CTE, subquery, window, `HAVING`, non-equality join, or ambiguous-column cases produce diagnostics.

## Constraint-Planning.md

# Constraint Planning

The planner merges schema constraints with extracted query requirements, searches deterministic candidate values, allocates a bounded set of witness scenarios, and refuses unsatisfiable requests rather than weakening the schema. For example, a query requiring `COMPLETED` conflicts with an enum that permits only `OPEN` and `CLOSED`.

## Relational-Coverage.md

# Relational Coverage

The compiler creates valid equality-join witnesses and validates declared primary-key and foreign-key relationships for supported acyclic schemas. Advanced multi-column joins, bridge-table multiplicity, self references, and cycles remain planned relational phases.

## Coverage-Reports.md

# Coverage Reports

`result.coverage_report()` reports explicit covered and total counts for predicate states, joins, boundaries, and requested negative cases. Unsupported requirements, uncovered states, warnings, and validation status remain visible. Percentages apply only to the documented supported subset.

## Evaluation-Methodology.md

# Evaluation Methodology

The repository includes a reproducible missing-filter experiment comparing schema-only, query-aware, and contract-to-test generation on one controlled fixture. Treat it as a method demonstration, not a universal performance or defect-detection claim. See `benchmarks/methodology/benchmark_protocol.md` and `research/EXPERIMENTAL_METHODOLOGY.md`.

## Spark-Native-Generation.md

# Spark-Native Generation

Great Generator supports Spark in its established generation APIs. Contract-to-test witness materialization is Pandas-only in Phase 1 and fails clearly for `engine="spark"`; it does not silently collect a large Spark dataset on the driver. A native distributed implementation is planned and must pass a no-driver-materialization gate before it is documented as supported.

## Temporal-Consistency.md

# Temporal Consistency

SCD2 and CDC capabilities already exist in Great Generator, but a unified workload-aware temporal consistency engine is planned. Phase 1 contract-to-test reports do not claim historical dimension lookup or CDC-sequence coverage.

## FAQ.md additions

### Does contract-to-test execute my SQL?

No. It parses supported SQL into a workload contract. The compiler does not connect to a database or run supplied SQL.

### Is 100% in the coverage report the same as complete SQL coverage?

No. It means every measured requirement in the explicit supported denominator was covered. Unsupported SQL constructs remain listed separately.

### Are invalid records mixed into the valid dataset?

No. Requested invalid examples are returned as separately labeled negative datasets so the valid baseline remains suitable for integrity checks.
