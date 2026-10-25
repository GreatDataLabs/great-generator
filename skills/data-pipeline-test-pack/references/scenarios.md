# Scenario construction versus pipeline validation

| Case | Current mechanism | Required check |
|---|---|---|
| Happy | Schema/relational generator | Counts, declared keys, bounds/types |
| Endpoints | Fixed values on a copy of generated rows | Both endpoints present, no corruption of happy fixture |
| Null/duplicate/orphan/outlier | Opt-in domain/relational anomaly rates; or labeled deterministic example mutation | Count actual failures, keep valid baseline |
| CDC envelopes | `generate_cdc("banking", "customers", rows=..., operations=[...])` | Operation, before/after, keys, delay and duplicate flags |
| Domain SCD2 | `generate_history("banking", "customers", ...)` | Positive non-overlapping intervals, unique scd_id, exactly one current row |
| New/changed/unchanged | Copy a base frame; choose disjoint keys, change one attribute, add a fresh key | Explicit expected differences; not a core selector |
| Query-sensitive cases | Optional query profile | Marginal coverage plus actual branch assertions |

Core domain/relational anomaly rate names include `null_rate`, `duplicate_rate`,
`orphan_fk_rate`, `late_arrival_rate`, `out_of_order_rate`, `outlier_rate`,
`skew_rate`, `negative_amount_rate`, `invalid_status_rate`. Inspect installed
configuration before applying. Rates are not exact scenario guarantees, especially
on small fixtures. Validate observed output; use explicitly constructed cases when
exact counts are needed. Null/negative/duplicate cases in the runnable example are
documented transformations, not demonstrations of a new injector API.

CDC `before`/`after` values are JSON strings. Inserts have no before image; deletes
have no after image. Generated sequence numbers do not establish event-time order.
Events may repeat keys and are not a coherent state machine. Never feed the raw
stream blindly to Delta MERGE. Deduplication and conflict policy must be explicit.

SCD2 uses `scd_id`, natural key, `effective_from`, `effective_to`, `is_current`.
Treat intervals as half-open `[from, to)` for these examples. The generator's
current rows use a far-future end, not NULL. Historical values are synthetic version
variants; do not assume every version conforms to a regulated business lifecycle.

The runnable pack proves fixture properties, not ETL correctness. A runner should
record expected pipeline results, actual results and error details separately.
Only claim a scenario passed end-to-end after both construction and downstream
assertions run. Save package/runtime/seed, schemas, rules, and exact transformations.
