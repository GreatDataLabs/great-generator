# Relationships and scale

```python
data = generate_relational(
    tables={
        "customers": {"schema": "customer_id int primary key, name string", "rows": 12},
        "orders": {
            "schema": "order_id int primary key, customer_id int references customers.customer_id",
            "rows": 48,
        },
    },
    seed=42,
)
customers, orders = data["customers"], data["orders"]
```

Relationships can instead be supplied as
`["orders.customer_id -> customers.customer_id"]`. When using parsed
`TableSchema` instances, explicitly extract/pass supported single-column FK edges;
the current relational table adapter otherwise discards FK metadata. Do not flatten
composite keys to their first member. SQL-qualified names may need an explicit
reviewed name mapping for the compact relational relationship syntax.

Before generation:
- Non-empty children with non-null FKs need non-empty parents.
- One-to-one child references require enough distinct parents and an explicit
  construction/check; the normal many-to-one sampler does not guarantee uniqueness.
- Parent PK and child FK representations must be compatible.
- The supported graph is acyclic. Self-references require a separately designed
  fixture; removing the edge silently creates a different contract.
- Preserve CHECK/unique/default diagnostics; a parsed constraint is not necessarily
  enforced by the generator. Do not claim full SQL contract satisfaction.

Pandas needs memory for all tables. `generate_relational(engine="spark")` uses
native distributed generation, but values/semantic options differ from the Pandas
path. Generic `generate_from_schema(..., engine="spark")` and domain-model helpers
can build Pandas first. Do not switch APIs merely to claim scale while losing rules.
Measure a bounded sample and review resources before large volumes.

`check_keys` returns actual checks for declared single-column PK/FKs. It fails a
request with missing columns, checks only non-null FK values against parents, and
requires `non_nullable=[("orders", "customer_id")]` for required FKs. It does not
check CHECK expressions, SQL collation, composite constraints or business cardinality.

Exported tables are not automatically loaded in a database, registered in a catalog,
or made atomic as a group. Report partial writes and do not delete prior outputs to
hide a failure. A manifest records requested and validated counts separately.
