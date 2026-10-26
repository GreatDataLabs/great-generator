# Prior art and technical differentiation

## Scope and conclusion

Schema- and query-aware test-data generation is established research. Relational synthesis,
constraint solving, mutation-killing datasets, structural SQL coverage, property-based testing,
and DBMS fuzzing all predate this project. Great Generator must not claim invention of those ideas.

The testable project hypothesis is narrower:

> A lightweight developer library that combines existing enterprise contract adapters, SQL AST
> requirements, deterministic relational generation, bounded witness scenarios, and explicit
> coverage reports may improve pipeline-defect detection over this project's schema-only and
> value-injection baselines for supported workloads.

That is a hypothesis, not a proven general result.

## Technical comparison

| Project or method | Primary approach | Relevant overlap | Difference to test, not assume |
|---|---|---|---|
| [Faker](https://faker.readthedocs.io/en/master/) | Provider-based fake values with localization | Semantic scalar values | Great Generator compiles multi-table contracts and SQL witnesses; Faker is still reused for values |
| [SDV](https://docs.sdv.dev/sdv/) | Learns generative models from real single-, sequential-, or multi-table data; supports constraints | Relational synthesis and constraints | Great Generator creates contract-defined test fixtures without fitting production rows; statistical fidelity is not the Phase 1 objective |
| [Databricks Labs dbldatagen](https://databrickslabs.github.io/dbldatagen/) | Spark-native generation specifications, repeatability, constraints, multiple tables and CDC | Distributed and relational generation | The proposed contribution is workload-to-witness compilation and measured SQL condition coverage, not Spark generation itself |
| [GenRocket](https://www.genrocket.com/synthetic-data-generation/) | Commercial by-design test-data automation, permutations, negative cases and referential integrity | Test-case-directed data and coverage language | Vendor documentation already describes coverage-oriented synthetic test data; comparative claims require access and fair evaluation |
| [MOSTLY AI](https://mostly.ai/docs/generators/tabular-synthetic-data) | Trained generative models for single/multi-table and sequential data with relationship configuration | Multi-table integrity and realistic distributions | Great Generator's compiler targets deterministic pipeline-test witnesses rather than learned fidelity or privacy claims |
| [Hypothesis](https://hypothesis.readthedocs.io/en/latest/) | Property-based generation and shrinking from strategies | Edge cases, reproducibility, generated tests | Phase 1 emits relational SQL witnesses and coverage artifacts; shrinking and broad property exploration are not implemented |
| [SQLsmith](https://github.com/anse1/sqlsmith) | Random valid SQL query generation | Database testing workloads | Great Generator consumes user SQL and generates data; it does not generate random SQL in Phase 1 |
| [SQLancer](https://github.com/sqlancer/sqlancer) | DBMS logic/performance testing using generated statements, test oracles, and query-plan guidance | Oracles, database states and feedback-guided testing | Great Generator targets data-pipeline workload fixtures, not DBMS engine correctness or plan exploration |
| [XData](https://arxiv.org/abs/1411.6704) | Constraint generation aimed at killing classes of SQL mutations | Schema + query constraints, mutation testing, expected differences | This is the closest prior art; Great Generator's current distinctive engineering target is integration with its schema adapters and DataFrame/lakehouse workflows, not a novelty claim |
| [Structural Coverage Criteria for Testing SQL Queries](https://www.jucs.org/jucs_15_3/structural_coverage_criteria_for.html) | SQL-specific test adequacy criteria over query structure and data | Predicate and join coverage | Phase 1 uses a smaller explicitly bounded criterion and must not label it complete SQL structural coverage |
| [QAGrow: Constraint-based Test Database Generation for SQL Queries](https://giis.uniovi.es/testing/papers/ast-2010-qagrow.pdf) | Query-aware constraint-based database generation | Query semantics and coverage-guided data | Demonstrates that query-aware constraint generation is prior art |
| [Search-Based Test Data Generation for SQL Queries](https://repository.tudelft.nl/record/uuid%3A90a6431f-f78f-4ac3-bf87-c052cd9cd5d4) | Search and query-plan fitness over SQL coverage targets | Joins, WHERE coverage, automated data generation | Phase 1 is constructive and bounded, not search-based; comparative effectiveness remains untested |
| [DOMINO](https://eprints.whiterose.ac.uk/id/eprint/127821/) | Coverage-driven data for relational integrity-constraint testing | Constraint boundary and negative tests | Great Generator also considers query workloads; DOMINO remains important prior art for schema-constraint coverage |
| [Relational symbolic execution of SQL code](https://doi.org/10.1016/j.scico.2015.03.005) | Translates SQL/database behavior into SMT constraints and uses Z3 | Solver-backed relational test generation | Phase 1 deliberately avoids a mandatory solver and therefore supports a smaller constraint class |

## Defensible current difference

The implemented Phase 1 combination is practically differentiated inside this project by:

1. reusing schema contracts from SQL DDL and existing normalized models;
2. parsing user SELECT workloads into inspectable predicate/join contracts;
3. constructing deterministic TRUE/FALSE/UNKNOWN and boundary witnesses;
4. preserving a clean relational baseline while isolating intentional invalid cases;
5. reporting explicit covered/total denominators and unsupported syntax; and
6. returning ordinary Pandas DataFrames plus portable JSON/HTML artifacts.

No broad originality claim follows from this combination. The first local controlled experiment is
evidence for one fixture only. Broader mutation, solver, Spark, temporal, and external-tool studies
are required before a research claim can be assessed.

## Sources and verification notes

Sources above are official documentation, project repositories, or published/repository papers.
Commercial capability descriptions are attributed to vendor documentation and were not independently
validated. Absence of a feature was not inferred from a homepage alone.
