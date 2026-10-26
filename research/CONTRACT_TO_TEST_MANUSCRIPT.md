# Contract-to-Test: Coverage-Driven Synthetic Data Generation for Enterprise Data Pipeline Validation

## Status

Technical manuscript draft. Results are limited to the executed fixtures cited below; broader experiments are pending.

## Abstract

Data pipeline tests often use schema-valid random data that does not exercise the predicates, joins, boundaries, and NULL behavior present in the workload under test. This work investigates a contract-to-test method that parses a documented SQL subset, combines extracted requirements with schema constraints, and allocates deterministic synthetic witness rows. The current implementation supports a Pandas execution path, explicit coverage denominators, bounded boolean assertions, and separated negative datasets. A controlled missing-filter fixture demonstrates the evaluation method, but is not sufficient to establish broad effectiveness or originality.

## 1. Introduction

Schema conformance is necessary but not sufficient for pipeline testing. A dataset may have valid types and keys while never reaching a branch used by an important query. Great Generator's proposed contribution is therefore evaluated at the intersection of schema contracts, SQL workload requirements, deterministic generation, and measured test-condition coverage.

## 2. Problem formulation

Given a normalized relational schema contract `S`, a supported SQL workload `Q`, row budgets `R`, and seed `z`, produce datasets `D`, scenario metadata `W`, and a coverage report `C` such that:

1. the clean baseline satisfies supported constraints in `S`;
2. each claimed witness in `W` is independently evaluated against its extracted requirement;
3. repeated compilation with the same inputs and environment is reproducible;
4. unsupported SQL or unsatisfiable requirements remain visible rather than being silently ignored; and
5. intentional violations are separated from the valid baseline.

## 3. Related work

The method builds on established ideas from fake-value generation, statistical synthetic data, property-based testing, constraint-based database testing, query fuzzing, and SQL test-data generation. Detailed source links and overlap analysis are maintained in [PRIOR_ART_AND_TECHNICAL_DIFFERENTIATION.md](PRIOR_ART_AND_TECHNICAL_DIFFERENTIATION.md).

## 4. Architecture

All supported schema inputs normalize into Great Generator's existing schema models. SQL is parsed into an immutable workload contract. A deterministic planner derives bounded scenarios, the existing generation engine creates a baseline, scenario materialization injects witnesses, and an independent three-valued evaluator validates the outcomes. See [CONTRACT_TO_TEST_ARCHITECTURE.md](../docs/engineering/CONTRACT_TO_TEST_ARCHITECTURE.md).

## 5. Contract normalization and workload analysis

Phase 1 accepts normalized schema models, relational mappings, SQL DDL, and JSON/YAML contract files. It analyzes a documented top-level `SELECT` subset without connecting to a database or executing supplied SQL. Unsupported constructs produce structured diagnostics.

## 6. Constraint planning and coverage-driven generation

Candidate values come from schema enums, ranges, query literals, adjacent boundary values, and typed defaults. Scenarios include all-true, one-false, nullable UNKNOWN, boundary, and equality-join witnesses. Candidate assignments are validated against schema constraints; conflicts raise actionable errors.

## 7. Relational and temporal consistency

The current compiler validates primary keys, uniqueness, simple and composite foreign-key tuples, row counts, and supported equality joins. Generic cyclic planning, broad multi-column join planning, and unified SCD2/CDC workload coverage are pending research phases.

## 8. Experimental setup

The first controlled fixture mutates a query by removing a status filter and compares schema-only, existing query-aware, and contract-to-test generation. The script, methodology, and environment capture live under `benchmarks/contract_to_test/` and `benchmarks/methodology/`.

## 9. Results

The local fixture in `benchmarks/reports/contract_to_test_missing_filter_local.json` records one observed defect detection by the contract-to-test strategy and no detection by the two baselines under that exact setup. This is one fixture, not a population estimate or general claim. Multi-workload, multi-seed, cross-engine results are pending.

## 10. Threats to validity

- The executed evaluation contains one hand-checked mutation.
- Scenario materialization currently uses Pandas.
- The SQL subset and bounded oracle omit many SQL semantics.
- The project authors designed both the method and initial fixture.
- External-tool and independent-replication comparisons are pending.

## 11. Limitations

See [RESEARCH_LIMITATIONS.md](RESEARCH_LIMITATIONS.md). In particular, a coverage value of 100% applies only to an explicit supported denominator and must not be read as complete SQL coverage.

## 12. Conclusion

Phase 1 establishes a working and falsifiable research artifact: SQL requirements become deterministic witnesses, witnesses are validated independently, and a controlled defect can be tested reproducibly. Broader effectiveness, scale, and originality remain questions for subsequent experiments.
