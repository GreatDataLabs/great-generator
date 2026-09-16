# JSON Schema Ingestion

Great Generator can generate synthetic data from a practical subset of JSON Schema using `generate_from_json_schema`.

The JSON Schema is normalized into the same schema-first generation path used by `generate_from_schema`. There is no separate JSON Schema generation engine.

## Quickstart

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

You can also pass a path to a JSON Schema file:

```python
df = generate_from_json_schema("schemas/customer.schema.json", rows=1000)
```

## Supported v1 subset

| JSON Schema feature | Support | Behavior |
|---|---:|---|
| `type: object` | Yes | Required for the top-level schema |
| `properties` | Yes | Each property becomes a column |
| `required` | Yes | Required columns are generated without null injection from this path |
| `string` | Yes | Generates realistic string values when semantic names are recognized |
| `integer` | Yes | Maps to `int` |
| `number` | Yes | Maps to `float` |
| `boolean` | Yes | Maps to `bool` |
| `array` | Basic | Maps to an array-like type where supported by the base generator |
| `format: email` | Yes | Uses the semantic email generator |
| `format: date` | Yes | Uses date generation |
| `format: date-time` | Yes | Uses datetime generation |
| `enum` | Yes | Generated values are constrained to the enum values |
| `minimum` / `maximum` | Yes | Passed as numeric range rules |
| `minLength` / `maxLength` | Yes | Applied as string length constraints where practical |
| `description` | Metadata | Preserved as schema-source context where applicable |
| `default` | Metadata/rule | Used as fallback metadata; not a replacement for generation rules |

## Unsupported or partial features

These features are intentionally not treated as fully supported in this release:

- `oneOf`
- `anyOf`
- `allOf`
- `not`
- `patternProperties`
- external `$ref`
- recursive schemas
- deep nested object graphs
- complex arrays of objects

By default, unsupported keywords raise a clear validation error. Use `strict=False` only when you want Great Generator to ignore unsupported metadata and proceed with the supported subset.

```python
df = generate_from_json_schema(json_schema, rows=1000, strict=False)
```

## Notes

- JSON Schema ingestion creates synthetic data from a schema contract. It does not validate or transform production records.
- For deeply nested API payload generation, use this v1 path for flat record tables and treat full nested OpenAPI support as roadmap work.
- The returned object is a DataFrame, so you can write it using Pandas or Spark-native APIs depending on your runtime.
