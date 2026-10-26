# Problem statement

Schema-valid synthetic rows are not necessarily useful test rows. A pipeline defect can remain
invisible when generated records never satisfy the relevant join path, predicate combination, NULL
state, or boundary. The engineering problem is to transform a data contract and a supported SQL
workload into a small, deterministic set of relational witnesses while preserving clean-data
constraints except in explicitly labeled negative datasets.

## Research hypothesis

For supported SQL and contract subsets, contract-to-test generation will expose more seeded pipeline
defects per generated row than schema-only or unconstrained value generation.

This hypothesis needs mutation experiments across multiple schemas and engines. One successful local
fixture is not sufficient evidence of general effectiveness.

## Non-goals

- privacy transformation or anonymization of production rows;
- statistical reproduction of a production population;
- complete SQL semantics;
- proof of query equivalence;
- DBMS engine fuzzing;
- universal performance claims.
