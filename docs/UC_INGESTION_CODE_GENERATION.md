# Unity Catalog ingestion notebook generation

`generate_uc_ingestion_code(...)` creates a reviewable Databricks notebook plus metadata, relationship, validation, and manifest artifacts. It never executes the notebook or writes tables.

```python
from great_generator import generate_uc_ingestion_code

artifacts = generate_uc_ingestion_code(
    source_table="retail.sales.fact_orders",
    include_related=True,
    target_catalog="synthetic_sandbox",
    target_schema="sales_demo",
    rows={
        "dim_customer": 100_000,
        "dim_product": 10_000,
        "fact_orders": 5_000_000,
    },
    format="delta",
    output="databricks_notebook",
    output_path="generated/retail_pipeline.ipynb",
    execute=False,
    spark=spark,
)
```

Output:

```text
generated/
  retail_pipeline.ipynb
  generation_config.yaml
  relationships.json
  schema_snapshot.json
  validation_report.json
  generation_manifest.json
```

The configuration file uses JSON syntax, which is valid YAML 1.2, so the feature does not add a required YAML dependency.

## Notebook flow

1. Explain prerequisites and metadata-only behavior.
2. Configure source, rows, relationship strategy, and target namespace.
3. Inspect UC metadata and display the graph.
4. Generate Spark DataFrames through the existing engine.
5. Validate PK/FK integrity.
6. Preview bounded samples.
7. Display target mappings.
8. Keep the modifying cell behind `ENABLE_WRITES = False`.
9. Use `errorifexists`, never overwrite, when a user deliberately enables writes.

## Safety controls

- `execute=True` is rejected.
- Target catalog/schema must differ from the source catalog/schema.
- Identifiers are quoted and escaped.
- No tokens, passwords, or workspace credentials are written to artifacts.
- No unrestricted `DROP`, source-table write, or broad destructive SQL is generated.
- The generated validation report starts as `not_run`; running the notebook produces the real report.

The notebook builder creates code. It does not grant permissions, create infrastructure, or approve a sandbox on the user's behalf.
