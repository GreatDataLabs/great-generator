# Constraint-planning algorithm

## Constructive Phase 1 planner

For each query and requested state assignment:

1. group predicates by resolved table-qualified column;
2. build a deterministic candidate set from contract enums, min/max values, SQL literals,
   predecessor/successor boundary values, midpoints, and type-specific fallback values;
3. coerce each candidate to the contract data type;
4. reject candidates that violate nullability, enums, ranges, or string length;
5. evaluate every predicate on that column using SQL three-valued semantics; and
6. choose the first candidate satisfying all desired states.

If no candidate exists, the planner raises `UnsatisfiableScenarioError` with the column, schema
allowed values, workload requirements, and a resolution message. It never expands an enum or range
silently.

## Complexity

For `p` predicates and at most `c` candidates per referenced column, the constructive search is
bounded approximately by `O(p*c)` for independent column groups. This is not a complete constraint
solver and cannot prove satisfiability for arbitrary computed or cross-column expressions.

## Future solver boundary

An optional SMT backend may be justified for complex arithmetic, composite constraints, cycles, and
cross-column rules. It must remain optional and produce the same inspectable scenario contract.
