# Unity Catalog schema snapshots and drift detection

Unity Catalog snapshots are metadata-only, JSON-serializable, and fingerprinted independently of capture time.

```python
from great_generator import inspect_unity_catalog_table

snapshot = inspect_unity_catalog_table(
    "retail.sales.fact_orders",
    include_related=True,
    spark=spark,
)
snapshot.save("fact_orders_schema.json")
```

Compare reviewed snapshots:

```python
from great_generator import compare_uc_schema_snapshots

diff = compare_uc_schema_snapshots(
    old="fact_orders_schema.json",
    new="fact_orders_schema_latest.json",
)

print(diff.to_text())
if diff.changed:
    print(diff.as_dict())
```

The report detects:

- added and removed tables;
- added and removed columns;
- SQL type changes;
- nullability changes;
- primary-key changes;
- added and removed relationships.

Snapshots intentionally exclude records and credentials. Their hash covers the normalized metadata graph, not the capture timestamp. Comparison is read-only: Great Generator never migrates UC schemas or overwrites generation plans automatically.
