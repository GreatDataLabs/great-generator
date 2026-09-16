# API Reference

## `generate_from_schema(...)`

The primary API for generating a DataFrame from a schema you already have.

```python
generate_from_schema(
    schema,
    rows=100,
    seed=None,
    engine="auto",
    spark=None,
    table_name="sample",
    realism="realistic",
    domain=None,
    custom_rules=None,
    plan=None,
    realistic=None,
    validate=False,
    return_report=False,
    required_values=None,
    partition_by=None,
    target_selectivity=None,
    query_profile=None,
)
```

Supported inputs are plain mappings, Pandas dtype mappings, Pandas DataFrames, compact DDL strings, parsed SQL DDL `ContractSchema` objects, PySpark `StructType`, PySpark DataFrames, `TableSchema`, and `DomainSchema`.

See [SCHEMA_INPUTS.md](SCHEMA_INPUTS.md) and [CONTRACTS_AND_DDL.md](CONTRACTS_AND_DDL.md) for the exact support matrix and limitations.

## Schema-source ingestion APIs

These APIs normalize external schema documentation into the existing `generate_from_schema` path.

### `generate_from_json_schema(...)`

```python
from great_generator import generate_from_json_schema

df = generate_from_json_schema(json_schema, rows=1000)
```

Supports the documented v1 JSON Schema subset: top-level object, properties, required fields, scalar types, `format: email`, `format: date`, `format: date-time`, enums, and numeric min/max bounds.

### `generate_from_dbt_schema(...)`

```python
from great_generator import generate_from_dbt_schema

df = generate_from_dbt_schema("models/schema.yml", model_name="customers", rows=1000)
```

Maps common dbt column metadata, including `data_type`, `not_null`, `unique`, and `accepted_values` tests.

### `generate_from_dbt_manifest(...)`

```python
from great_generator import generate_from_dbt_manifest

df = generate_from_dbt_manifest("target/manifest.json", model_name="customers", rows=1000)
```

Reads common dbt `manifest.json` model nodes under `nodes`.

### `load_data_dictionary(...)` and `generate_from_data_dictionary(...)`

```python
from great_generator import generate_from_data_dictionary, load_data_dictionary

schema = load_data_dictionary("data_dictionary.csv")
df = generate_from_data_dictionary("data_dictionary.csv", rows=1000)
```

Supports CSV, YAML, and JSON data dictionaries with practical fields such as `column_name`, `data_type`, `nullable`, `allowed_values`, `min`, `max`, `unique`, `primary_key`, `foreign_key`, and `pii_class` metadata.

## `parse_ddl(...)`

Parses one or more SQL `CREATE TABLE` statements into a canonical `ContractSchema`. This is the contract-first entry point when your source of truth is database, warehouse, lakehouse, Spark, or Databricks DDL.

```python
from great_generator import generate_from_schema, parse_ddl

ddl = """
CREATE TABLE sales.customers (
  customer_id BIGINT PRIMARY KEY,
  customer_name STRING NOT NULL,
  email VARCHAR(120) UNIQUE
);

CREATE TABLE sales.orders (
  order_id BIGINT PRIMARY KEY,
  customer_id BIGINT NOT NULL,
  amount DECIMAL(12, 2),
  FOREIGN KEY (customer_id) REFERENCES sales.customers(customer_id)
)
"""

contract = parse_ddl(ddl, dialect="databricks", strict=True)
print(contract.fingerprint())

customers = generate_from_schema(contract.tables["sales.customers"], rows=1000)
```

Signature:

```python
parse_ddl(
    ddl_text,
    dialect="ansi",
    strict=True,
    name="ddl_contract",
)
```

Supported dialect values are `"ansi"`, `"spark"`, and `"databricks"` for the documented subset. Strict mode raises `ContractParseError` for unsupported contract-affecting syntax. Permissive mode returns warnings only when the base contract can still be represented safely. Unknown type conversion and malformed keys remain errors.

## `generate_domain(...)`

Generates a built-in enterprise domain pack and returns a dictionary of DataFrames.

Important parameters:

- `domain`: built-in domain name, for example `banking`, `ecommerce`, `healthcare`, `telecom`, or `saas`
- `engine`: `"pandas"` or `"spark"`
- `scale`: `"tiny"`, `"small"`, `"medium"`, or `"large"`
- `rows`: optional per-table row-count overrides
- `realism`: `"realistic"` or `"placeholder"`
- `seed`: optional integer for reproducible output
- `anomalies`: opt-in data quality issues
- `return_labels`: optional pandas anomaly label table named `_anomaly_labels`
- `history`: optional `"scd2"` history generation for pandas domains
- `output_path` and `output_format`: optional convenience exports

```python
data = generate_domain("ecommerce", scale="small", realism="realistic", seed=42)
```

## Schema generation details

Generates a single DataFrame or domain-shaped dictionary from schema metadata. Single-table schema generation is semantic-field based: it normalizes column names, expands common abbreviations, combines column-name intent with data type, and generates realistic values where possible.

Supported inputs:

- compact DDL strings such as `"id int, name string"`
- SQL `CREATE TABLE` contracts created with `parse_ddl(...)`
- Python mappings such as `{ "customer_name": "string", "age": "int" }`
- empty pandas DataFrames with dtypes
- PySpark `StructType`
- PySpark DataFrames
- `TableSchema`
- `DomainSchema`
- one-table or multi-table `ContractSchema`

```python
df = generate_from_schema(
    {"customer_name": "string", "email_id": "string", "age": "int"},
    rows=100,
    domain="retail",
)
```


Realistic schema mode applies clean data-quality defaults:

- ages stay within realistic ranges and align with `date_of_birth` when present
- business dates are not future dates by default
- `updated_at` follows `created_at`, and `end_date` follows `start_date`
- status-aware fields use logical nulls such as no `payment_date` for pending payments
- ID fields are unique and are not confused with normal numeric columns
- `realism="realsitic"` is accepted as a typo alias with a warning

Important optional parameters:

- `domain`: optional preset such as `banking`, `retail`, `healthcare`, `insurance`, `hr`, or `education`
- `custom_rules`: per-column overrides for values, min/max ranges, semantic type, prefixes, uniqueness, and date ranges
- `plan`: optional `GenerationPlan` from `infer_generation_plan(...)`
- `realistic`: set `False` for older placeholder-style values
- `realism`: string mode, `"realistic"` or `"placeholder"`; `"clean"` maps to realistic, `"basic"` and `"simple"` map to placeholder
- `validate`: optional post-generation data quality check
- `return_report`: return `(dataframe, report)` when you want the validation report with the generated data
- `required_values`: optional query-aware values that must appear in generated columns
- `partition_by`: optional query-aware partition values or custom counts for one column
- `target_selectivity`: optional approximate ratios for specific filter values
- `query_profile`: optional reusable mapping containing query-aware options

## Advisor APIs

Advisors are optional and run before generation. They produce JSON artifacts that can be inspected, edited, saved, and reused.

```python
from great_generator import generate_from_schema, infer_generation_plan

schema = "customer_id int, customer_name string, email string"
plan = infer_generation_plan(schema, advisor="none")
df = generate_from_schema(schema, rows=1000, plan=plan)
```

### `infer_generation_plan(...)`

Creates a `GenerationPlan` for a schema.

```python
infer_generation_plan(
    schema,
    advisor="none",
    hints=None,
    cache_path=".gg_cache/",
    refresh_cache=False,
)
```

### `tag_schema(...)`

Creates `ColumnTags` for PII class, business semantic, and suggested masking.

```python
tag_schema(
    schema,
    advisor="none",
    samples=None,
    cache_path=".gg_cache/",
    refresh_cache=False,
)
```

### `review_realism(...)`

Reviews a generated sample against a `GenerationPlan`.

```python
review_realism(
    data,
    plan,
    advisor="none",
    sample_size=500,
    cache_path=".gg_cache/",
)
```

`advisor="none"` is always offline and never reads API keys.

## `generate_relational(...)`

Generates user-defined parent/child tables with valid primary-key and foreign-key relationships.

```python
data = generate_relational(
    tables={
        "customers": {"schema": "customer_id int primary key, customer_name string", "rows": 1000},
        "orders": {"schema": "order_id int primary key, customer_id int references customers.customer_id", "rows": 10000},
    },
    engine="pandas",
    realism="realistic",
)
```

Query-aware relational generation also accepts table-qualified `required_values`, a mapping-style `partition_by`, `target_selectivity`, `ensure_join_coverage`, and `query_profile`.

```python
data = generate_relational(
    tables=tables,
    required_values={
        "dim_member.region": ["SOUTH"],
        "dim_product.product_type": ["CHECKING", "SAVINGS"],
    },
    partition_by={
        "table": "fact_interaction",
        "column": "business_date",
        "values": ["2026-01-01", "2026-01-02"],
        "distribution": "balanced",
    },
    ensure_join_coverage=True,
)
```

See [QUERY_AWARE_GENERATION.md](QUERY_AWARE_GENERATION.md) for details and limitations.

## `generate_cdc(...)`

Generates CDC-style records with operation type, before/after payloads, event timestamp, ingestion timestamp, sequence number, source system, late-arrival flag, and duplicate flag.

```python
cdc = generate_cdc("banking", table="customers", rows=10000, seed=42)
```

## `export_data(...)`

Writes a dictionary of tables to CSV, JSON, Parquet, or Delta.

Returned DataFrames are always preserved, so users can also write with native pandas or Spark APIs.


## `generate_from_recipe(...)`

Generates a domain or relational dataset from a declarative JSON, TOML, or simple YAML recipe.

```python
from great_generator import generate_from_recipe

data = generate_from_recipe("banking_recipe.yaml")
```

Recipes are useful when a dataset needs to be reproduced for a demo, benchmark, lab, or paper.

## `generate_history(...)`

Generates an SCD2 history table for a single domain table.

```python
from great_generator import generate_history

history = generate_history("banking", table="customers", history_window="2y")
```

The result includes `effective_from`, `effective_to`, and `is_current`.

## `generate_dimensional_model(...)`

Generates a relational dimensional model from a domain pack.

```python
from great_generator import generate_dimensional_model

model = generate_dimensional_model("ecommerce", scale="small")
fact_sales = model["fact_sales"]
dim_customer = model["dim_customer"]
```

Ecommerce and banking include domain-aware fact and dimension tables. Other domains receive a generic fact/dimension split.

## `generate_data_vault_model(...)`

Generates a relational Data Vault model from a domain pack.

```python
from great_generator import generate_data_vault_model

vault = generate_data_vault_model("banking", scale="small")
hub_customer = vault["hub_customer"]
```

The output includes hubs, links, satellites, stable hash keys, load dates, record source values, and model metadata.


## `validate_generated_data(...)`

Validates generated schema data for common quality expectations.

```python
from great_generator import generate_from_schema, validate_generated_data

schema = {"email": "string", "age": "int", "customer_id": "string"}
df = generate_from_schema(schema, rows=100)
result = validate_generated_data(df, schema)
```

Returns a dictionary with `passed`, `errors`, `warnings`, and `summary`.

## `validate_query_coverage(...)`

Validates query-aware coverage after generation.

```python
from great_generator import validate_query_coverage

report = validate_query_coverage(
    data=df,
    required_values={"region": ["SOUTH"]},
    partition_by={
        "column": "business_date",
        "values": ["2026-01-01", "2026-01-02"],
    },
    target_selectivity={"region": {"SOUTH": 0.25}},
)
```

The report includes required-value status, partition coverage, partition counts, selectivity actuals and targets, join coverage status, warnings, and an overall `passed` flag.

## `explain_generation_plan(...)`

Explains how each schema field will be interpreted before generation.

```python
from great_generator import explain_generation_plan

plan = explain_generation_plan({
    "cust_nm": "string",
    "emp_age": "int",
    "txn_amt": "double",
    "created_ts": "timestamp",
})

print(plan["semantic_coverage"])
print(plan["fields"])
```

Each field includes the column name, dtype, inferred semantic type, confidence, reason, and generator description.
