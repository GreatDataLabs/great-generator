# Feature gap analysis: contract-driven pipeline testing

**Audit baseline:** `c58f4d8` (`great-generator` 0.1.8)

**Audit date:** 2026-10-25
**Baseline test run:** 334 tests collected; 306 passed and 28 were skipped. Skips were optional
Spark, Delta, Hugging Face, and environment-dependent paths. This is a local Windows/Python
3.13 result, not a cross-platform guarantee.

This audit uses package code and tests as evidence. README statements were not treated as proof.

| Capability | Baseline implementation | Missing functionality at audit | Reusable components | Phased work |
|---|---|---|---|---|
| Schema normalization | `ContractSchema`, `DomainSchema`, `TableSchema`; SQL DDL, JSON Schema, dbt, data dictionary, Pandas and PySpark adapters | One public compiler that accepts these sources and a workload together | `great_generator.schemas`, `great_generator.contracts` | Phase 1 normalizes supported schema/DDL inputs into `DomainSchema`; direct adapter composition remains documented |
| Query-aware generation | Required values, selectivity, partitions, and basic parent-value join coverage for Pandas | No SQL parsing; no TRUE/FALSE/UNKNOWN witnesses; no boundary compiler | `great_generator.query_aware` | Phase 1 adds an AST workload compiler and bounded witnesses |
| SQL parser | SQLGlot-backed DDL parser | No SELECT workload contract or unsupported-query diagnostics | SQLGlot is already a core dependency by ADR 0003 | Phase 1 adds a documented SELECT subset |
| Relational constraints | Parent-first simple PK/FK generation; UC adapter repairs and validates composite FK tuples | Generic Pandas generation uses one primary-key column and first-column FK generation; cycles/self-references rejected; no cardinality profiles | `DomainSchema.dependencies`, `topological_sort`, relational schema parser | Phase 1 reuses clean acyclic generation; composite/cyclic expansion remains Phase 2 |
| Spark-native generation | Multi-table schema/domain generation uses `spark.range`; deterministic hash expressions for supported scalar columns | Single-table `generate_from_schema(engine="spark")` first creates Pandas; query-aware options reject Spark; no distributed workload witnesses | `great_generator.engines.spark_engine` | Phase 3; Phase 1 fails explicitly instead of silently collecting |
| Temporal generation | Pandas SCD2 history helper; CDC events; UC SCD2 and portable CDC wrappers | No fact-to-version as-of assignment; no unified temporal state model; incomplete temporal validators | `great_generator.history`, `great_generator.cdc` | Phase 3 |
| Validation | Seed tests, simple FK validation, UC PK/unique/composite-FK validation, query-aware value coverage | No SQL predicate-state denominator, scenario ledger, or independently derived bounded oracle | `validate_query_coverage`, UC validation | Phase 1 adds scenario and coverage validation |
| Evaluation tooling | Repeatable dataset/query templates and result templates | No controlled mutation harness or baseline comparison | Existing retail benchmark assets | Phase 1 adds one executed missing-filter experiment; broader evaluation is Phase 5 |
| Unity Catalog | Metadata-only inspection, related-table discovery, generation, CDC, snapshots, validation, review-first notebooks | Cross-catalog inference, cyclic graphs, Spark query-aware witnesses, and automatic temporal facts | `great_generator.integrations.databricks` | Phase 4 integrates UC snapshots with the workload compiler |
| Advisors | Optional local/hosted design-time advisors and deterministic saved plans | Advisor output is not a proof of query coverage | `GenerationPlan`, advisor registry/cache | Keep advisory only; the compiler uses validated ASTs and deterministic rules |
| MCP | Optional generation, parsing, relational, validation, and export tools | No contract-to-test MCP tool in Phase 1 | Existing lazy MCP server | Consider after API stabilization |

## Important implementation evidence

- `generate_single_table_spark()` calls `generate_single_table_pandas()` and then
  `spark.createDataFrame()`. It is not a large-scale native path.
- `spark_engine._generate_schema_driven()` uses `spark.range()` and Spark expressions for the
  current multi-table scalar path; it does not collect all generated rows first.
- `query_aware.apply_query_aware_relational_pandas()` supports value and join-path preparation,
  but it does not parse or evaluate SQL predicates.
- `relationships.graph.topological_sort()` raises on cycles. This is correct fail-fast behavior,
  not cyclic relationship support.
- `TableSchema` can represent composite keys, while the generic generation path still primarily
  materializes its first key column. Representation and execution support are therefore different.
- Unity Catalog reads metadata only by default and does not prove that all catalog constraints are
  declared or enforced by the source platform.

## Phase 1 reuse decision

The contract-to-test layer must not become a second synthetic data engine. It performs:

```text
schema + SQL -> normalized requirements -> deterministic witness plan
                                               |
                                               v
                         existing Pandas relational generator
                                               |
                                               v
                     bounded witness materialization + validation
```

Spark-native witness materialization needs a separate implementation because reusing the current
single-table Spark wrapper would violate the no-driver-materialization requirement.

## Status legend

- **Implemented:** covered by code and tests in the named scope.
- **Partial:** representation or a subset exists, but important cases are absent.
- **Experimental:** usable for evaluation with explicit limitations.
- **Blocked:** unsafe or misleading without an architectural prerequisite.
- **Planned:** not implemented.
