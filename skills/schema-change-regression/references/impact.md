# Contract impact boundaries

The helper accepts existing `ContractSchema` instances and compares
`canonical_dict()` fields. It emits `TABLE_ADDED`, `TABLE_REMOVED`, `COLUMN_ADDED`,
`COLUMN_REMOVED`, `TYPE_CHANGED`, `NULLABILITY_CHANGED`, `DEFAULT_CHANGED`,
`CONSTRAINT_CHANGED`, `PK_CHANGED`, `FK_CHANGED`, `COLUMN_ORDER_CHANGED` and
`METADATA_CHANGED`. A type change may produce several field-level entries.

- Removed tables/columns, tightened nullability, PK/FK changes and PK type changes
  receive high review priority.
- Nullable additions and relaxed nullability receive low review priority.
- Other changes require review: even a widened string can affect snapshots,
  downstream serializers or distribution tests.
- Renames appear as removal/addition. Do not guess identity from similar names.
- CHECK/default strings are compared, not executed. Equivalent expressions can
  still appear changed. This is not a SQL migration or theorem-proving engine.
- FK dependency closure is conservative for all table changes. It does not prove
  every dependent fixture must change. Union old/new graphs to catch removed FKs.
- Contract-level metadata changes conservatively mark all fixtures for review.
  Fingerprints include metadata and source dialect, not only physical columns.

`affected_fixtures` includes removed objects; `regenerable_tables` excludes removed
tables but is **not** a standalone generation plan. Generation needs unchanged
parents too. Safest small-fixture approach: regenerate the full reviewed related
set in a new namespace, or reuse exact saved parents and an explicit compatible
child fixture strategy. Do not invent a "reuse parent" option on the core API.

For targeted regeneration, record a dependency closure and preserve untouched
artifacts. If existing APIs cannot constrain children to saved parent keys, explain
that limitation and obtain agreement to rebuild the related set.

Regressions include requested row counts, key uniqueness/nullability, orphan counts,
new bounds/categories, query-relevant branches, and changed/unchanged scenario
expectations. Hash equality is not a data-content check. Do not compare Spark
physical order or file partition layout as a logical equality test.
