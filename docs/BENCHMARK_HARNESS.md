# Synthetic benchmark harness

The benchmark harness helps users generate repeatable synthetic datasets and SQL query templates for their own Databricks, Microsoft Fabric, Snowflake, local Spark, or Spark-style environments.

These benchmark examples are designed to help users generate repeatable synthetic datasets and query templates for their own environments. They are not universal performance claims. Results depend on warehouse size, cluster configuration, storage layout, file format, statistics, clustering, caching, concurrency, and query engine settings.

## Folder layout

```text
benchmarks/
  datasets/retail_star_schema/
  queries/retail_star_schema/
  databricks/
  fabric/
  snowflake/
  local_spark/
  results_template/
```

## Implemented dataset

`retail_star_schema` is implemented with:

- `dim_customer`
- `dim_product`
- `dim_store`
- `dim_date`
- `fact_sales`

The fact table includes `business_date`, `region`, `product_category`, and `sales_channel` so users can test partition filters, selective filters, joins, and aggregations.

## Generate benchmark data

```bash
python benchmarks/datasets/retail_star_schema/generate_dataset.py   --output output/retail_star_schema   --format parquet   --overwrite
```

Use `--scale-factor` to change the dataset size:

```bash
python benchmarks/datasets/retail_star_schema/generate_dataset.py   --output output/retail_star_schema   --format parquet   --scale-factor 0.1   --overwrite
```

## Query templates

Templates are available in `benchmarks/queries/retail_star_schema/`:

- `q01_partition_filter.sql`
- `q02_join_aggregation.sql`
- `q03_selectivity_filter.sql`
- `q04_monthly_rollup.sql`
- `q05_large_groupby.sql`

Adapt database, schema, catalog, path, and table names to your platform.

## Platform examples

| Platform | Example |
|---|---|
| Databricks | `benchmarks/databricks/retail_star_schema_benchmark.ipynb` |
| Microsoft Fabric | `benchmarks/fabric/retail_star_schema_benchmark.ipynb` |
| Snowflake | `benchmarks/snowflake/retail_star_schema_benchmark.sql` |
| Local Spark | `benchmarks/local_spark/retail_star_schema_benchmark.ipynb` |

## Record results

Use:

```text
benchmarks/results_template/benchmark_results_template.csv
benchmarks/results_template/benchmark_report_template.md
```

Record platform, engine version, cluster or warehouse size, dataset, scale factor, file format, partitioning, query name, run number, cold/warm status, elapsed seconds, rows returned, bytes scanned, and notes.

## Limitations

- Do not use these templates as platform rankings.
- Do not compare platforms unless configuration is controlled and documented.
- Synthetic data does not reproduce production distribution, layout, statistics, caching, or workload concurrency unless you explicitly model those factors.
- Great Generator does not anonymize, mask, de-identify, or transform production data.
