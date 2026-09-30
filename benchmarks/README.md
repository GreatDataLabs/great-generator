# Synthetic benchmark harness

These benchmark examples are designed to help users generate repeatable synthetic datasets and query templates for their own environments. They are not universal performance claims. Results depend on warehouse size, cluster configuration, storage layout, file format, statistics, clustering, caching, concurrency, and query engine settings.

## Implemented dataset

| Dataset | Status | Tables |
|---|---|---|
| `retail_star_schema` | Implemented | `dim_customer`, `dim_product`, `dim_store`, `dim_date`, `fact_sales` |
| `customer_360` | Roadmap placeholder | Planned customer profile and interaction data |
| `iot_timeseries` | Roadmap placeholder | Planned device telemetry and event data |

## Generate the retail star schema

```bash
python benchmarks/datasets/retail_star_schema/generate_dataset.py --output output/retail_star_schema --format parquet --overwrite
```

Use `--scale-factor` to increase or reduce row counts in your own environment.

## Run query templates

SQL templates are in `benchmarks/queries/retail_star_schema/`. Adapt database, schema, catalog, path, and table names for Databricks, Fabric, Snowflake, or local Spark.

## Record results

Use `benchmarks/results_template/benchmark_results_template.csv` to record runtime details, run number, cold/warm status, elapsed seconds, rows returned, bytes scanned, and notes.

Do not compare results across platforms unless you control cluster size, warehouse size, file format, layout, table statistics, cache state, concurrency, and query settings.
