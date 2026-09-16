# Supported Schema Inputs

`generate_from_schema` is the primary entry point when you already know the structure of the data you need. Great Generator also includes optional loaders that normalize common schema-documentation formats into the same generation path.

All schema inputs are normalized into the existing generation engine. No second generation engine is introduced for JSON Schema, dbt metadata, or data dictionaries.

## Current support matrix

| Input type | Supported | Function | Notes |
|---|---:|---|---|
| Python dict | Yes | `generate_from_schema` | Existing `{column: dtype}` mappings |
| Compact DDL string | Yes | `generate_from_schema` | Existing one-table column strings such as `"id int, name string"` |
| Full SQL `CREATE TABLE` DDL | Yes | `parse_ddl`, `generate_from_schema` | Documented ANSI/Spark/Databricks subset |
| Pandas DataFrame | Yes | `generate_from_schema` | Empty or populated DataFrame schemas |
| Pandas dtype mapping | Yes | `generate_from_schema` | `df.dtypes.to_dict()` |
| PySpark `StructType` | Yes | `generate_from_schema` | Requires PySpark only when Spark objects are used |
| PySpark DataFrame | Yes | `generate_from_schema` | SparkSession is inferred when available |
| JSON Schema | Yes | `generate_from_json_schema` | Practical v1 subset: object/properties/scalars/enums/ranges/formats |
| dbt `schema.yml` | Yes | `generate_from_dbt_schema` | Optional YAML support through `great-generator[dbt]` |
| dbt `manifest.json` | Yes | `generate_from_dbt_manifest` | Common dbt manifest model nodes |
| Data dictionary CSV/YAML/JSON | Yes | `load_data_dictionary`, `generate_from_data_dictionary` | Enterprise schema documentation files |
| `TableSchema` | Yes | `generate_from_schema` | Native typed schema object |
| `DomainSchema` | Yes | `generate_from_schema` | Returns a dictionary of generated tables |
| Pydantic model | Planned | TBD | Roadmap |
| SQLAlchemy model | Planned | TBD | Roadmap |
| OpenAPI schema | Planned | TBD | Roadmap |
| Dataclass | Planned | TBD | Roadmap |

## Plain mapping

```python
from great_generator import generate_from_schema

schema = {
    "customer_id": "string",
    "customer_name": "string",
    "email": "string",
    "age": "int",
    "balance": "float",
    "created_at": "datetime",
}

df = generate_from_schema(schema, rows=1000)
```

## Pandas schema

```python
import pandas as pd

from great_generator import generate_from_schema

empty = pd.DataFrame(
    {
        "customer_id": pd.Series(dtype="int64"),
        "customer_name": pd.Series(dtype="string"),
        "age": pd.Series(dtype="int64"),
        "balance": pd.Series(dtype="float64"),
        "created_at": pd.Series(dtype="datetime64[ns]"),
    }
)

from_frame = generate_from_schema(empty, rows=1000)
from_dtypes = generate_from_schema(empty.dtypes.to_dict(), rows=1000)
```

## Compact DDL

```python
df = generate_from_schema(
    "customer_id string, customer_name string, age int, balance decimal(12,2)",
    rows=1000,
)
```

Supported compact forms include `name type`, `name:type`, and Spark-style `struct<name:type,...>`. Compact DDL is intentionally lightweight and does not carry table-level metadata. Use full SQL DDL when you need keys, constraints, schema-qualified names, or canonical hashing.

## Full SQL CREATE TABLE DDL

Use `parse_ddl` when your contract is SQL DDL rather than a compact column list. The parser uses SQLGlot and supports the documented ANSI, Spark, and Databricks subset.

```python
from great_generator import generate_from_schema, parse_ddl

contract = parse_ddl(
    """
    CREATE TABLE sales.customers (
      customer_id BIGINT PRIMARY KEY,
      customer_name STRING NOT NULL,
      email VARCHAR(120) UNIQUE,
      created_at TIMESTAMP DEFAULT current_timestamp()
    )
    """,
    dialect="databricks",
)

df = generate_from_schema(contract, rows=1000)
```

For multiple tables, `parse_ddl` returns a `ContractSchema` containing each table keyed by its qualified name.

## JSON Schema

```python
from great_generator import generate_from_json_schema

json_schema = {
    "type": "object",
    "required": ["customer_id", "email"],
    "properties": {
        "customer_id": {"type": "integer"},
        "email": {"type": "string", "format": "email"},
        "signup_date": {"type": "string", "format": "date"},
        "status": {"type": "string", "enum": ["ACTIVE", "INACTIVE", "PENDING"]},
        "balance": {"type": "number", "minimum": 0, "maximum": 10000},
    },
}

df = generate_from_json_schema(json_schema, rows=1000)
```

See [JSON Schema ingestion](JSON_SCHEMA.md) for the supported v1 subset and limitations.

## dbt metadata

```python
from great_generator import generate_from_dbt_schema, generate_from_dbt_manifest

df = generate_from_dbt_schema(
    "models/schema.yml",
    model_name="customers",
    rows=1000,
)

from_manifest = generate_from_dbt_manifest(
    "target/manifest.json",
    model_name="customers",
    rows=1000,
)
```

Install YAML support when loading dbt `schema.yml` files:

```bash
pip install "great-generator[dbt]"
```

See [dbt integration](DBT_INTEGRATION.md).

## Data dictionaries

```python
from great_generator import generate_from_data_dictionary, load_data_dictionary

schema = load_data_dictionary("data_dictionary.csv")
df = generate_from_data_dictionary("data_dictionary.csv", rows=1000)
```

Supported file types are CSV, YAML, and JSON. See [data dictionary ingestion](DATA_DICTIONARY.md).

## PySpark StructType

```python
from pyspark.sql import types as T

from great_generator import generate_from_schema

schema = T.StructType(
    [
        T.StructField("customer_id", T.StringType(), False),
        T.StructField("customer_name", T.StringType(), True),
        T.StructField("age", T.IntegerType(), True),
        T.StructField("balance", T.DoubleType(), True),
        T.StructField("created_at", T.TimestampType(), True),
    ]
)

spark_df = generate_from_schema(schema, rows=1000, engine="spark")
```

If the runtime cannot discover an active session, pass `spark=spark`. Single-table Spark schema generation currently generates values locally before creating the Spark DataFrame, so choose row counts that fit the driver. Spark-native arbitrary-schema generation is planned.

## Business rules

Use a simple schema plus `custom_rules`:

```python
rules = {
    "customer_id": {"prefix": "CUST"},
    "customer_name": {"type": "full_name"},
    "age": {"min": 18, "max": 85},
    "status": {"values": ["Active", "Inactive", "Pending"]},
    "created_at": {"start": "2024-01-01", "end": "2024-12-31"},
}

df = generate_from_schema(schema, rows=1000, custom_rules=rules)
```

Supported rules include `type`, `min`, `max`, `values`, `weighted_values`, `prefix`, `pattern`, `start`, `end`, `null_rate`, and the validation expectation `unique`.

## Output behavior

- Mapping, compact DDL, one-table SQL DDL contracts, JSON Schema, dbt, data dictionary, Pandas, and `TableSchema` inputs return a Pandas DataFrame by default.
- Spark context or `engine="spark"` returns a Spark DataFrame where that input path supports Spark output.
- A PySpark DataFrame carries its own schema and Spark session.
- `DomainSchema` and multi-table `ContractSchema` inputs return a dictionary of table-name to DataFrame.

The returned DataFrame remains yours to write to CSV, JSON, Parquet, Delta, a database, or cloud storage.
