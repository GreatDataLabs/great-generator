# Map SQL needs to supported controls

| Requirement | Existing control | Extra evidence |
|---|---|---|
| `region='SOUTH'` | `required_values={"region": ["SOUTH"]}` | Presence does not set a percentage |
| `product_type IN (...)` | Required values list | Check every desired group after joins |
| Known business dates | `partition_by={"column": "business_date", "values": [...], "distribution": "balanced"}` | Counts; specify `table` for multi-table data |
| Desired marginal fraction | `target_selectivity={"region": {"SOUTH": .25}}` | `selectivity_actuals`, not exact compound-predicate selectivity |
| Join-path participation | `ensure_join_coverage=True` on `generate_relational` | Explicit relationships and actual joined result |
| Shared config | `query_profile={...}` | Direct arguments may override profile values; record final config |

Use `table.column` keys for multi-table required values/selectivity. The query
`partition_by` mapping controls values; writer partitioning uses column lists and
does not itself ensure any date is present.

Ranges, expression predicates, NULL/NOT NULL branches, HAVING and windows need
explicit cases and assertions beyond marginal coverage. Do not advertise a generic
automatic translator. For impossible requirements (one row but two required values,
fractions totaling above one, non-empty children with empty required parents), stop
and ask which constraint to adjust.

Coverage report fields are `required_values_status`, `partition_coverage_status`,
`partition_counts`, `selectivity_actuals`, `selectivity_targets`,
`join_coverage_status`, `warnings`, and `passed`. Never replace these with an
unsubstantiated "100% coverage" label. Add explicit SQL branch assertions separately.

For a positive-only tiny fixture, concentrating a dimension on SOUTH and assigning
both product categories makes desired groups easier to guarantee. Label that
choice: it is a query fixture, not a calibrated population model. Add nonmatching
dates/categories in a separate negative fixture and verify exclusion.

Query-aware generation helps synthetic data match expected query values,
partition dates, and join paths. It does not guarantee identical production
performance because file layout, table statistics, clustering, caching,
concurrency, warehouse size, and query engine configuration also affect runtime.
