# dbt Integration

Great Generator can generate synthetic data from common dbt metadata so analytics engineers can test models, joins, contracts, and BI logic without relying on production records.

Supported entry points:

```python
from great_generator import generate_from_dbt_schema, generate_from_dbt_manifest
```

## Install

`schema.yml` parsing uses YAML support:

```bash
pip install "great-generator[dbt]"
```

`manifest.json` parsing uses the Python standard library.

## Generate from dbt schema.yml

```yaml
version: 2

models:
  - name: customers
    description: Customer dimension table
    columns:
      - name: customer_id
        data_type: integer
        description: Unique customer identifier
        tests:
          - unique
          - not_null
      - name: email
        data_type: string
      - name: status
        data_type: string
        tests:
          - accepted_values:
              values: ["ACTIVE", "INACTIVE", "PENDING"]
```

```python
from great_generator import generate_from_dbt_schema

df = generate_from_dbt_schema(
    path="models/schema.yml",
    model_name="customers",
    rows=1000,
)
```

## Generate from dbt manifest.json

```python
from great_generator import generate_from_dbt_manifest

df = generate_from_dbt_manifest(
    path="target/manifest.json",
    model_name="customers",
    rows=1000,
)
```

The manifest loader supports common dbt manifest model nodes under `nodes` with `resource_type: model`, `name`, and `columns` metadata.

## Metadata mapping

| dbt metadata | Great Generator behavior |
|---|---|
| `name` | Column name |
| `data_type` | Column dtype |
| `description` | Semantic hint / metadata |
| `not_null` test | Required/non-null expectation |
| `unique` test | Unique value expectation for generated output |
| `accepted_values` test | Allowed enum values |
| `relationships` test | Preserved as relationship metadata where possible; full relational construction remains explicit through `generate_relational` |

## Recommended analytics workflow

1. Generate a DataFrame from the dbt model metadata.
2. Write it to a local file, warehouse staging table, or lakehouse path using your normal DataFrame writer.
3. Run dbt models or tests against the generated lower-environment dataset.
4. Add query-aware options when SQL filters or partitions require specific values.

## Limitations

- This integration reads dbt metadata. It does not run dbt commands.
- It does not inspect a database connection or warehouse catalog.
- It supports common `schema.yml` and `manifest.json` structures, not every possible package-specific metadata extension.
