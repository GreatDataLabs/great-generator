# Contract-first roadmap backlog

This backlog records future milestones without adding premature public APIs or placeholder modules.

## M1B: Additional contract inputs

- rich inline schema metadata
- Avro
- Pydantic
- OpenAPI
- Unity Catalog metadata

Implemented before this roadmap milestone: JSON Schema, dbt `schema.yml`, dbt `manifest.json`, and CSV/YAML/JSON data dictionary ingestion for the documented v1 subsets.

## M1C: Semantic and deterministic-generation foundation

- versioned semantic registry
- confidence-based semantic inference
- evidence signals
- strict inference
- deterministic table, column, row, and batch seeds
- strict validation modes

## M1D: Relational generation

- composite-key generation
- multiple foreign keys
- nullable foreign keys
- self-references
- dependency graph
- cycle strategies
- cardinality distributions
- relational validation

## M2: Native Spark execution

- `spark.range`-based generation
- Spark SQL expression compilation
- partition-independent deterministic values
- direct Delta writes
- incremental batches
- Spark-native validation
- Databricks and Fabric examples
- scalable benchmark harness

## M3: Enterprise test scenarios

- valid, invalid, and mixed datasets
- deterministic anomaly injection
- referential-integrity failures
- duplicates
- schema drift
- malformed raw output
- lifecycle state machines
- CDC
- SCD1 and SCD2
- late-arriving data
- streaming event sequences

## M4: Evaluation and observability

- generation manifest
- data profiles
- rule coverage
- requested-versus-produced distributions
- relationship metrics
- transparent quality dimensions
- runtime and throughput metrics
- JSON and self-contained HTML reports

## M5: Optional source-aware synthesis

- aggregate-only profiling
- category weights
- numeric histograms
- null rates
- cardinality patterns
- date seasonality
- limited explainable correlation support
- optional SDV synthesis backend
- fidelity evaluation
- explicit privacy documentation

Future synthesis backends must remain separate from execution engines. Pandas and Spark describe where generation runs; rules or future statistical synthesis describe how values are produced.
