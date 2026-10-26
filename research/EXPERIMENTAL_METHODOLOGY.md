# Experimental methodology

The initial evaluation uses controlled SQL mutations and three applicable generation strategies:

1. schema-only generation;
2. existing query-aware value injection; and
3. contract-to-test witness generation.

Each experiment fixes schema, query, row counts, and seed. It defines a reference transformation,
introduces exactly one mutation, executes both on each dataset, and records whether outputs differ.
Generation and query execution are timed separately. Environment versions and content hashes are
captured at execution time.

The first experiment removes an order-status filter. Its protocol is in
`benchmarks/methodology/benchmark_protocol.md`; the runnable implementation is
`benchmarks/contract_to_test/run_missing_filter_evaluation.py`.

Future studies require multiple schemas, mutations, seeds, repetitions, and engines. Timing claims
require cold/warm separation and controlled compute, storage, statistics, and concurrency.
