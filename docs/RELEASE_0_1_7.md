# Great Generator 0.1.7

Release date: 2026-08-15

Great Generator 0.1.7 focuses on contract-first generation, query-aware test data, and clearer launch documentation.

## Highlights

- Added `parse_ddl(...)` for documented SQL `CREATE TABLE` ingestion.
- Added canonical schema contracts with stable fingerprints and structured parser diagnostics.
- Added support for the documented ANSI, Spark, and Databricks DDL subset.
- Added generation from one-table parsed DDL contracts through `generate_from_schema(...)`.
- Added optional query-aware generation for required values, partition dates, target selectivity, and relational join coverage.
- Added `validate_query_coverage(...)` for query coverage reports.
- Added a runnable retail star-schema example with DDL contracts, deterministic business rules, relationship validation, and manifest output.
- Added generation manifest, determinism, provenance, benchmark methodology, recipe authoring, and data-quality integration documentation.
- Refreshed the GitHub Pages site and PyPI-facing README so users can understand schema-first, SQL DDL, query-aware, advisor, Spark, and relational workflows.

## Why it matters

This release makes Great Generator more than a simple fake-value generator. Users can start from the contracts they already have, such as schemas, SQL DDL, DataFrames, Spark schemas, and relationship definitions, then generate synthetic data that is useful for lower environments, ETL testing, joins, lakehouse demos, CDC checks, and reproducible examples.

## Important notes

- Great Generator creates synthetic data. It does not anonymize, mask, de-identify, or transform production records.
- Query-aware generation helps generated data contain expected values, partition dates, selectivity targets, and join paths. It does not guarantee identical production performance.
- Full composite-key and cyclic relational generation is still deferred to a later relational milestone.
- Spark-native query-aware generation is planned. Current query-aware shaping is implemented for Pandas generation paths.

## Install

```bash
pip install --upgrade great-generator
```

Optional extras:

```bash
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

## Links

- PyPI: https://pypi.org/project/great-generator/
- Documentation: https://greatdatalabs.github.io/great-generator/
- GitHub: https://github.com/GreatDataLabs/great-generator
- Changelog: https://github.com/GreatDataLabs/great-generator/blob/main/CHANGELOG.md
