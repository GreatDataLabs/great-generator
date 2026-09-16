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
