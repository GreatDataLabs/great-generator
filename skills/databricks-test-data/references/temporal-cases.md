# CDC, SCD2 and medallion test fixtures

## CDC and Delta MERGE

`generate_cdc` currently supports banking customers and returns Pandas events with
JSON before/after payloads. It is not a stateful transaction log. It may produce
multiple events per customer and labeled duplicates. Sequence order is not event
time. Agree on ordering/deduplication before constructing a MERGE source.

[cdc_merge.py](../examples/cdc_merge.py) demonstrates a bounded independent-case
fixture: discard labeled duplicates, choose highest sequence per key, derive the
initial target from selected before images, then derive the expected target from
after images. This makes insert/update/delete preconditions explicit. It projects
customer_id/status only; it does not replay all attributes or history.

1. Call `build_case()` locally and inspect `(initial, source, expected)`.
2. Verify source has one non-null key per customer. The helper rejects ambiguous
   sequence numbers and mismatched payload keys. Check every desired operation
   is actually represented; a small random sample does not guarantee the mix.
3. With approval, write `initial` to a **new disposable** Delta table, safe mode.
4. Call `merge_into_test_table(..., approved_target=target)` only when the user
   explicitly wants update/delete behavior on that target.
5. Compare the resulting table to `expected` using distributed two-way differences
   and row counts. Only then report the MERGE case passed. Rerun requires a fresh
   target or an explicit reset decision; do not overwrite automatically.

The helper validates unique target keys but is not a transaction isolation or
concurrency controller. Actual Databricks/UC permissions and Delta behavior require
a configured runtime test. Offline fixture tests do not certify those operations.

## SCD Type 2

Use `generate_history(domain, table, seed=..., history_window="2y")` for supported
domain history. It returns Pandas, not native distributed history. Validate small
history before conversion, then check Spark types/timezone after conversion.

Use `scd_id` as version key; the natural entity key repeats. Require one current
version per entity, unique surrogate IDs, positive `[effective_from, effective_to)`
intervals and no overlaps. Current rows use a far-future end, not null. Natural-key
uniqueness is the wrong assertion on an SCD2 table.

For new/changed/unchanged tests, retain a generated baseline, copy disjoint keys,
change an explicit attribute, preserve unchanged rows, and assign a fresh key to
new entities. These are deterministic scenario transformations, not extra
`generate_history` options. Do not claim the skill implements a general SCD2 MERGE.
If installed, the pipeline-test-pack skill supplies a runnable construction and
interval checker; otherwise use the above invariants directly.

## Medallion and queries

Create source fixtures and expected assertions for the user's Bronze/Silver/Gold
pipeline; do not rebuild the pipeline. Stage positive, invalid, late and duplicate
cases separately. Watermark and quarantine outcomes require actual pipeline tests.

Query-aware generation remains Pandas-only. Small explicitly bounded fixtures may
be converted to Spark and tested against approved read-only SQL. Large native
query-aware Spark generation is a gap, not a capability unlocked by a skill.
