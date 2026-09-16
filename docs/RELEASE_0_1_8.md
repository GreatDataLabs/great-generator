# Great Generator 0.1.8

Great Generator 0.1.8 focuses on schema-source ingestion, optional assistant tooling, documentation quality, and organization-link consistency after the project moved to GreatDataLabs.

## Highlights

- JSON Schema ingestion through `generate_from_json_schema(...)` for the documented v1 object/property subset.
- dbt metadata ingestion through `generate_from_dbt_schema(...)` and `generate_from_dbt_manifest(...)`.
- Data dictionary ingestion from CSV, YAML, and JSON through `generate_from_data_dictionary(...)` and `load_data_dictionary(...)`.
- Query-aware examples and coverage-report documentation for required values, partitions, selectivity, and joins.
- Optional MCP server support through `great-generator[mcp]` and the `great-generator-mcp` command.
- GitHub Pages SEO updates including sitemap, robots.txt, canonical URLs, social metadata, and structured data.
- GreatDataLabs GitHub organization and documentation links across package metadata, README, docs, citation metadata, and release guidance.
- Architecture diagram added to the README and documentation site.

## Install

```bash
pip install great-generator
```

Optional extras:

```bash
pip install "great-generator[spark]"
pip install "great-generator[delta]"
pip install "great-generator[dbt]"
pip install "great-generator[schema-ingest]"
pip install "great-generator[mcp]"
```

Install with a hyphen and import with an underscore:

```python
from great_generator import generate_from_schema

schema = "customer_id int, customer_name string, email string, signup_date date"
df = generate_from_schema(schema, rows=1000)
```

## Schema-source examples

```python
from great_generator import generate_from_json_schema

df = generate_from_json_schema(
    {
        "type": "object",
        "required": ["customer_id", "email"],
        "properties": {
            "customer_id": {"type": "integer"},
            "email": {"type": "string", "format": "email"},
            "signup_date": {"type": "string", "format": "date"},
            "status": {"type": "string", "enum": ["ACTIVE", "INACTIVE", "PENDING"]},
        },
    },
    rows=1000,
)
```

```python
from great_generator import generate_from_dbt_schema

df = generate_from_dbt_schema("models/schema.yml", model_name="customers", rows=1000)
```

```python
from great_generator import generate_from_data_dictionary

df = generate_from_data_dictionary("data_dictionary.csv", rows=1000)
```

## Documentation

- Documentation: https://greatdatalabs.github.io/great-generator/
- GitHub: https://github.com/GreatDataLabs/great-generator
- Changelog: https://github.com/GreatDataLabs/great-generator/blob/main/CHANGELOG.md
- PyPI: https://pypi.org/project/great-generator/

## Notes

Great Generator creates synthetic non-production data. It does not anonymize, mask, de-identify, or transform production records. For very large datasets, use environment-appropriate row counts, chunking, or Spark-native paths.
