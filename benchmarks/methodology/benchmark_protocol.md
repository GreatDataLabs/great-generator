# Contract-to-Test benchmark protocol

This protocol separates **data generation**, **pipeline execution**, and **defect detection**.
It is intended for reproducible engineering evaluation, not promotional performance claims.

## Required controls

1. Use the same schema, workload, row counts, seed, and transformation for every applicable strategy.
2. Define a correct reference transformation before introducing one controlled mutation.
3. Record exact package, Python, engine, and platform versions.
4. Measure generation and execution separately with a monotonic clock.
5. Record both detected and undetected mutations.
6. Preserve unsupported outcomes; do not treat them as passes or failures.
7. Repeat timing studies and report dispersion before publishing performance conclusions.
8. Record cache state, partitions, file format, statistics, cluster/warehouse shape, and concurrency for distributed runs.

## Current local experiment

`benchmarks/contract_to_test/run_missing_filter_evaluation.py` compares:

- schema-only generation;
- existing query-aware generation; and
- the Phase 1 contract-to-test compiler.

The controlled defect removes the `order_status = 'COMPLETED'` predicate. A strategy detects
the defect when the correct and mutated transformations return different row counts. This is a
single bounded fixture and does not establish general superiority.

Run it with:

```bash
python benchmarks/contract_to_test/run_missing_filter_evaluation.py \
  --output benchmarks/reports/contract_to_test_missing_filter_local.json
```
