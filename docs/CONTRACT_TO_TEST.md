# Contract-to-Test synthetic data generation

`compile_test_dataset(...)` turns a supported schema contract and SQL workload into deterministic
Pandas datasets containing bounded predicate, join, NULL, and boundary witnesses.

It does not execute SQL, read production rows, or claim complete SQL coverage.

## When to use it

Use the compiler when tests need more than schema-valid random rows—for example, when a joined row
must satisfy a particular region, status, and date boundary, or when one predicate must be false
while the others remain true.

Use existing `generate_from_schema(...)` or `generate_relational(...)` when you only need general
fixtures, required values, selectivity, or partition dates.

## End-to-end example

```python
from great_generator.testing import compile_test_dataset

schema = {
    "dim_customer": {
        "schema": "customer_id int primary key, region string not null",
        "rows": 30,
    },
    "fact_orders": {
        "schema": (
            "order_id int primary key, "
            "customer_id int references dim_customer.customer_id, "
            "order_status string not null, "
            "order_date date not null, "
            "amount double"
        ),
        "rows": 60,
    },
}

query = """
SELECT c.region, COUNT(*) AS order_count
FROM fact_orders f
JOIN dim_customer c ON f.customer_id = c.customer_id
WHERE c.region = 'EAST'
  AND f.order_status = 'COMPLETED'
  AND f.order_date >= DATE '2026-01-01'
GROUP BY c.region
"""

result = compile_test_dataset(
    schema=schema,
    queries=[query],
    rows={"dim_customer": 30, "fact_orders": 60},
    coverage=["predicates", "joins", "boundaries", "null_handling"],
    seed=42,
)

customers = result.datasets["dim_customer"]
orders = result.datasets["fact_orders"]

validation = result.validate()
coverage = result.coverage_report()

result.export("./output/contract_test", format="parquet")
result.generate_report(
    format="html",
    output="./output/contract_test/coverage_report.html",
)
```

## Result contents

`ContractTestResult` provides:

- `datasets`: clean named Pandas DataFrames;
- `negative_datasets`: separate labeled invalid copies when `negative_cases` is requested;
- `workload`: parsed table, column, predicate, join, grouping, aggregate, and diagnostic metadata;
- `scenarios`: deterministic witness assignments and row bindings;
- `validation_report`: measured row-count, key, relationship, and witness validation;
- `coverage_report()`: explicit covered/total metrics;
- `expected_results`: bounded boolean-outcome assertions from a separate three-valued evaluator;
- `manifest`: hashes, seed, versions, environment, and safety metadata.

## SQL subset

Phase 1 supports a top-level `SELECT` with:

- `FROM`, `INNER JOIN`, and `LEFT JOIN`;
- column equality join conditions;
- `AND`, with OR/NOT represented but only partial combined-scenario guarantees;
- `=`, `!=`, `<`, `<=`, `>`, and `>=`;
- `IN`, `NOT IN`, `BETWEEN`, and `NOT BETWEEN` with literals;
- `IS NULL` and `IS NOT NULL`;
- numeric, string, Boolean, date, and timestamp literals;
- basic aggregate discovery and column `GROUP BY` discovery;
- aliases and schema-assisted unqualified-column resolution.

HAVING, CTEs, windows, subqueries, LIKE, computed predicates, non-equality joins, and
dialect-specific expressions produce diagnostics instead of silent approximations.

## Coverage meaning

The report calculates percentages only over an explicit supported denominator:

- predicate states: TRUE and FALSE, plus UNKNOWN for nullable columns when requested;
- supported equality join paths;
- supported query thresholds;
- currently supported labeled negative case types.

An empty denominator is `null`, not 100%. A report showing 100% means 100% of the documented
requirements extracted for that workload—not complete SQL semantic or pipeline coverage.

## Constraint conflicts

The planner checks nullability, accepted values, min/max values, and string length metadata where
available. It fails rather than silently widening a contract:

```text
Unable to satisfy the requested scenario:

column: fact_orders.order_status
schema_allowed_values: ['OPEN', 'CLOSED']
requirements: fact_orders.order_status = 'COMPLETED'=TRUE

Resolution: update the query profile or the schema contract.
```

## Negative cases

Add `"negative_cases"` to `coverage` to produce separate copies for the supported intentional
orphan-FK and unexpected-NULL cases. The clean baseline remains valid. Negative data is never mixed
into the clean `datasets` mapping.

## Schema inputs

The compiler accepts:

- `DomainSchema` or `ContractSchema`;
- relational table mappings used by `generate_relational(...)`;
- SQL `CREATE TABLE` DDL or a `.sql` file;
- JSON/YAML contract files with `tables` and optional `relationships`.

JSON Schema, dbt, data dictionaries, and Unity Catalog already normalize through existing adapters.
Direct one-call compiler adapters for those sources are planned; callers can currently pass their
normalized contract representation.

## Current limitations

- Pandas is the validated Phase 1 execution engine.
- Spark requests raise `NotImplementedError`; the compiler does not collect large Spark data into
  Pandas as a fallback.
- Generic composite-key execution, bridge cardinality, self-reference, and cycles remain Phase 2.
- Full-query result equivalence and arbitrary aggregate oracles are not claimed.
- Temporal SCD2/fact/CDC consistency is a later phase.
- The compiler generates synthetic data; it does not anonymize production data.

See the [feature-gap analysis](engineering/FEATURE_GAP_ANALYSIS.md),
[architecture](engineering/CONTRACT_TO_TEST_ARCHITECTURE.md), and
[research limitations](../research/RESEARCH_LIMITATIONS.md).
