# Unity Catalog relational generation

`generate_relational_from_unity_catalog(...)` discovers a bounded metadata graph, maps it to existing relational contracts, generates parent tables first, repairs composite FK tuples, and validates the result.

```python
from great_generator import generate_relational_from_unity_catalog

datasets, report = generate_relational_from_unity_catalog(
    table="retail.sales.fact_orders",
    include_related=True,
    related_direction="parents",
    relationship_strategy="declared",
    rows={
        "dim_customer": 100_000,
        "dim_product": 10_000,
        "fact_orders": 5_000_000,
    },
    output="spark",
    spark=spark,
    return_report=True,
)
```

The returned mapping is DataFrame-first:

```python
datasets["fact_orders"].write.format("delta").mode("errorifexists").saveAsTable(
    "synthetic_sandbox.sales_demo.fact_orders"
)
```

Great Generator does not choose or write targets unless the caller explicitly uses a writer.

## Relationship strategies

### Declared

`relationship_strategy="declared"` uses accessible UC PK/FK metadata only. This is the default.

### Inferred

`relationship_strategy="inferred"` keeps declared constraints and adds conservative suggestions only when a visible child `*_id` column matches exactly one visible parent PK column. Every suggestion carries `source="inferred"`, a confidence score, and evidence in the report. Inference is never promoted into Unity Catalog.

### Explicit

Use explicit mappings when constraints are missing:

```python
datasets = generate_relational_from_unity_catalog(
    "retail.sales.fact_orders",
    include_related=False,
    relationship_strategy="explicit",
    relationships={
        "fact_orders.customer_id": "dim_customer.customer_id",
        "fact_orders.product_id": "dim_product.product_id",
    },
    rows={"dim_customer": 1_000, "dim_product": 100, "fact_orders": 20_000},
    spark=spark,
    output="spark",
)
```

Explicit related tables are inspected in the root catalog/schema unless a three-part name is supplied.

## Validation report

`return_report=True` returns `(datasets, report)`. The report contains:

- metadata snapshot hash;
- declared/inferred/explicit relationship evidence;
- requested row counts;
- PK null and duplicate counts;
- simple and composite FK orphan counts;
- expected anomaly configuration;
- unexpected violations;
- a secret-free generation manifest.

## Query-aware data

The UC adapter forwards `required_values`, `partition_by`, `target_selectivity`, `ensure_join_coverage`, and `query_profile` to the existing engine. Use table-qualified fields for relational output.

Query-aware generation helps synthetic data match expected query values, partition dates, and join paths. It does not guarantee identical production performance because file layout, table statistics, clustering, caching, concurrency, warehouse size, and query engine configuration also affect runtime.

## Anomalies

Clean generation is the default. Pass core anomaly names (`null_rate`, `duplicate_rate`, `orphan_fk_rate`, and others documented in [`ANOMALIES.md`](ANOMALIES.md)) to create intentional violations. Friendly aliases `null_values`, `duplicate_records`, and `orphan_foreign_keys` are also accepted by the UC adapter.

## Unsupported graphs

Cycles and self-references require staged generation. The current adapter raises a clear error instead of silently returning invalid relationships. `relationship_profiles` and automatic dimensional-role transformation remain follow-up work because the current relational engine has no matching contract surface.
