# Unity Catalog metadata-driven examples

These notebooks show how Great Generator converts permitted Unity Catalog metadata into existing generation contracts and then uses the normal Pandas or Spark engines. Metadata inspection does **not** read source table records.

## Start without a Databricks workspace

The included `mock_uc_metadata.json` contains fictional retail metadata and no records. Every notebook uses it through:

```python
from great_generator import StaticUnityCatalogClient

client = StaticUnityCatalogClient.from_path(
    "examples/databricks/unity_catalog/mock_uc_metadata.json"
)
```

## Run in Databricks

Install the package, replace the fixture client with the active `spark` session, and use a table for which you have metadata visibility:

```python
from great_generator import inspect_unity_catalog_table

snapshot = inspect_unity_catalog_table(
    "catalog.schema.table",
    include_related=True,
    spark=spark,
)
```

Outside a notebook, install `great-generator[databricks]`, supply a SQL warehouse ID, and use Databricks unified authentication. Great Generator does not manage or persist credentials.

## Safety

- Examples do not write or overwrite catalog tables.
- Generated ingestion notebooks default to `ENABLE_WRITES = False` and `errorifexists`.
- Synthetic targets must use a different catalog/schema from the source.
- Great Generator produces synthetic data; it does not anonymize production records.
- Unity Catalog constraints are informational and may be incomplete because metadata is privilege-filtered.

For the complete API, permissions, supported types, and current limits, see [`docs/DATABRICKS_UNITY_CATALOG.md`](../../../docs/DATABRICKS_UNITY_CATALOG.md).
