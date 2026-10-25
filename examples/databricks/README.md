# Databricks examples

These notebooks show Great Generator usage patterns for Databricks, Spark, Delta Lake, DBFS, cloud storage, and Unity Catalog.

They do not create workspaces, clusters, catalogs, schemas, volumes, secrets, or credentials. Configure those in Databricks using your organization's normal controls.

## Unity Catalog metadata-driven generation

The [`unity_catalog/`](unity_catalog/README.md) series contains eleven offline-first notebooks for metadata inspection, single-table and relational generation, composite relationship validation, SCD2 history, portable CDC events, query-aware data, controlled anomalies, safe notebook generation, and schema drift detection. A fictional metadata fixture is included, so the workflow can be reviewed without cloud credentials.
