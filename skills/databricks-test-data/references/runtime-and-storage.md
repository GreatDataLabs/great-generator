# Runtime, schema and safe output

## Input and engine selection

| Need | API/path | Reality |
|---|---|---|
| StructType, empty PySpark DF, compact DDL | `generate_from_schema(..., engine="spark")` | Pandas generation first, then Spark conversion |
| Full Databricks DDL | `parse_ddl(..., dialect="databricks")` | Parses a documented subset; does not execute CREATE TABLE |
| Related user tables | `generate_relational(..., engine="spark")` | Native range-based path; validate semantics and forward FK list explicitly |
| Domain templates | `generate_domain(..., engine="spark")` | Native domain/generic Spark paths; supported features differ |
| Query profiles | Pandas generation + optional bounded conversion | No native Spark query-aware path |
| Domain dimensional/vault models | Existing model helpers | Local generation before Spark conversion; not unlimited scale |

Inspect `great_generator.__version__` and installed signatures. Install the core
into the notebook environment using its normal package mechanism; Databricks
already provides Spark. There is no `[databricks]` extra. Local Spark testing can
use `[spark]`; a local Delta session needs compatible `[delta]` jars/configuration.
Do not replace a managed runtime's Spark installation unnecessarily.

Use a supplied StructType directly or an explicitly approved table's `.schema`.
The core does not automatically introspect Unity Catalog. Catalog/schema/table
names in storage are not the same as the simple names supported in compact FK
strings: save a reviewed mapping and retain it in the manifest.

## Output contract

Keep `df`/`data` in memory unless delivery is requested:

```python
df = generate_from_schema(schema, rows=1000, engine="spark", seed=42)
# Execute ONLY after the user approves this exact new sandbox target:
# df.write.format("delta").mode("errorifexists").saveAsTable("sandbox.qa.customers_run_001")
```

`safe_delta.write_delta` accepts a simple three-level `catalog.schema.table` or an
explicit path; `approved_target` must match. This parameter documents prior human
approval, it does not obtain approval or confer permissions. `overwrite_confirmed`
must reflect an actual request to replace data, not an agent-generated assumption.

- Managed UC test table: `saveAsTable` without a custom path; storage is controlled
  by the catalog/schema. Do not auto-create catalogs or schemas.
- External/path output: `.save(path)` writes Delta files, **not** a registered UC
  table. Registering one is a separate approved operation with external-location
  permissions. A Volume path is a file destination, not a managed table name.
- DBFS root/mounts may be restricted or discouraged by the workspace; prefer
  approved UC destinations. `s3://`, `abfss://`, `gs://` depend on runtime connectors,
  identity and permissions; no credentials belong in generated code or manifests.
- Partition columns must exist; avoid high-cardinality partitioning and tiny
  files. Writer partitioning does not create missing partition dates.
- Append: check schema/types, existing data, keys and expected duplicate policy.
- Overwrite: identify data being replaced and get confirmation. Do not enable
  schema evolution to get around a mismatch. Atomicity across related tables is
  not supplied by these helpers; log partial writes honestly.

## Validation and manifests

`check_spark_keys` performs explicit distributed actions. A non-null FK is checked
with left anti-join; required FKs additionally need null checks. Other constraints
need Spark assertions. It does not enforce a business contract automatically.

Use `build_generation_manifest(..., engine="spark", validation=report)`.
It deliberately does not count Spark rows itself; include validated counts from
the report. Save schema/contract hash, seed, final arguments, package/runtime and
timezone/date context. Date-derived semantics can depend on today's date; pin
windows where supported. Do not compare file layout or physical row order.
