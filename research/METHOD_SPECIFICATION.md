# Method specification

## Inputs

- a normalized relational schema contract;
- one or more SQL SELECT workloads;
- requested coverage targets;
- row counts, realism mode, and seed.

## Phase 1 transformation

1. Parse SQL with SQLGlot without executing it.
2. Resolve table aliases and table-qualified columns against the schema.
3. extract atomic predicates, equality joins, grouping columns, aggregates, and diagnostics;
4. solve bounded column assignments for requested SQL truth states under enum/range/nullability rules;
5. allocate one distinct witness row per table and scenario;
6. generate the clean baseline through the existing Pandas relational engine;
7. materialize witness assignments and align declared FK/PK join values;
8. validate row counts, keys, foreign keys, predicate states, join equality, and boolean outcomes;
9. derive bounded expected assertions with a separate three-valued evaluator; and
10. report explicit covered and total requirements.

Intentional orphan and unexpected-NULL cases are deep-copied into separate labeled datasets.

## Current supported subset

- top-level `SELECT`, `FROM`, `INNER JOIN`, `LEFT JOIN`, and equality `ON` clauses;
- conjunctive `WHERE` guarantees;
- `=`, `!=`, `<`, `<=`, `>`, `>=`, `IN`, `NOT IN`, `BETWEEN`, `NOT BETWEEN`,
  `IS NULL`, and `IS NOT NULL` atomic predicates;
- literal numeric, string, Boolean, date, and timestamp values;
- recorded basic aggregates and `GROUP BY` columns.

OR and NOT are represented and evaluated, but do not yet receive full combined-condition guarantees.
Unsupported structures remain visible diagnostics.
