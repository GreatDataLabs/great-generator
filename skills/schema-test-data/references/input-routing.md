# Route the input, not the filename alone

| Input | Current API | Boundary |
|---|---|---|
| `{column: dtype}`; compact `id int, name string` | `generate_from_schema` | Rich rules go in `custom_rules`, not arbitrary dict values |
| Empty Pandas DataFrame or dtype mapping | `generate_from_schema` | Uses schema; production records are unnecessary |
| PySpark StructType or DataFrame | `generate_from_schema(..., engine="spark")` | Uses schema, not sampled rows; active Spark session or explicit `spark=` |
| Full CREATE TABLE DDL | `parse_ddl(..., dialect="ansi"/"spark"/"databricks")`, then `generate_from_schema(contract)` | Inspect diagnostics and constraints; multiple tables return a dict |
| JSON Schema object or JSON file | `generate_from_json_schema` | Top-level practical subset; ordinary schema dict API is not autodetection |
| dbt schema.yml | `generate_from_dbt_schema(path, model_name=...)` | Selected model only; optional `[dbt]` extra |
| dbt manifest.json | `generate_from_dbt_manifest(path, model_name=...)` | Metadata, not execution of dbt or full model DAG |
| CSV/YAML/JSON data dictionary | `generate_from_data_dictionary` | YAML needs `[schema-ingest]`; `load_data_dictionary` alone returns only types, losing rich rules |

JSON Schema supports primitive types, required, enum, numeric bounds, basic string
lengths and date/date-time/email formats. Do not promise full `$ref`, recursive,
composition or nested-object support; retain strict diagnostics. JSON *payload*
examples and nested JSON output are different APIs from JSON Schema ingestion.

DDL parsing preserves more metadata than generation enforces. CHECK/default
expressions and composite keys require explicit review; arbitrary expressions are
not executable instructions. Do not silently flatten composite relationships.

`generate_from_schema(..., return_report=True)` returns `(data, report)`; without
it return is a frame or a dict for multi-table contracts. Do not unpack a DataFrame
as if it were this tuple. Ingestion wrappers can postprocess data after an internal
report, so validate the final frame again.

Optional MCP can parse DDL and generate bounded local schema/relational artifacts.
It returns artifact paths/previews, not live Python/Spark DataFrames. If requested
input options aren't in the installed tool schema, use Python or report the gap.
Never send Spark/cloud/DB operations through the local-file MCP tool.
