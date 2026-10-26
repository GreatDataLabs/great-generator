# Evaluation results

## Current measured evidence

The repository includes one executed local controlled experiment:

`benchmarks/reports/contract_to_test_missing_filter_local.json`

For the recorded fixed schema, query, row counts, and seed:

- schema-only data did not expose the removed status filter;
- existing query-aware value injection did not expose it; and
- contract-to-test data exposed it with a validated predicate-false witness on the joined path.

The JSON file contains actual row counts, detected/undetected outcomes, durations, hashes, package
versions, platform data, and coverage denominators from that execution.

## Interpretation boundary

This result supports only the claim that the implemented witness method detected this mutation in
this fixture. It does not establish general superiority, production-scale performance, or statistical
significance. Broader results are pending Phase 5 experiments.
