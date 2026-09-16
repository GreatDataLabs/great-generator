# Data Dictionary Ingestion

Many teams document schemas in spreadsheets, CSV files, YAML files, or JSON files rather than application code. Great Generator supports CSV, YAML, and JSON data dictionaries for schema-first synthetic data generation.

## Public APIs

```python
from great_generator import generate_from_data_dictionary, load_data_dictionary
```

`load_data_dictionary` returns a simple `{column: dtype}` mapping:

```python
schema = load_data_dictionary("data_dictionary.csv")
```

`generate_from_data_dictionary` loads the dictionary, applies supported constraints, and returns a generated DataFrame:

```python
df = generate_from_data_dictionary("data_dictionary.csv", rows=1000)
```

## CSV format

Recommended columns:

```text
column_name,data_type,nullable,description,allowed_values,min,max,unique,primary_key,foreign_key,pii_class
```

Example:

```csv
column_name,data_type,nullable,description,allowed_values,min,max,unique
customer_id,integer,false,Unique customer identifier,,,,true
email,string,false,Customer email address,,,,true
status,string,false,Customer account status,"ACTIVE|INACTIVE|PENDING",,,
balance,decimal,true,Current balance,,0,10000,
```

```python
from great_generator import generate_from_data_dictionary

df = generate_from_data_dictionary("data_dictionary.csv", rows=1000)
```

## YAML format

```yaml
columns:
  - column_name: customer_id
    data_type: integer
    nullable: false
    unique: true
  - column_name: status
    data_type: string
    allowed_values: [ACTIVE, INACTIVE, PENDING]
```

## JSON format

```json
{
  "columns": [
    {"column_name": "customer_id", "data_type": "integer", "unique": true},
    {"column_name": "balance", "data_type": "decimal", "min": 0, "max": 10000}
  ]
}
```

## Supported metadata

| Field | Behavior |
|---|---|
| `column_name` | Required column name |
| `data_type` | Mapped to Great Generator dtype |
| `nullable` | `false` marks a column as required |
| `description` | Preserved as metadata / semantic hint |
| `allowed_values` | Constrains generated values to listed values |
| `min` / `max` | Numeric range rules where supported |
| `unique` | Unique value expectation for generated output |
| `primary_key` | Treated as a unique expectation for single-table output |
| `foreign_key` | Preserved as metadata; use `generate_relational` for enforced relationships |
| `pii_class` | Metadata only. It is not a compliance classifier and does not imply anonymization. |

## Important note about privacy

Great Generator creates synthetic records from schema documentation. It does not anonymize, mask, de-identify, or transform production records.
