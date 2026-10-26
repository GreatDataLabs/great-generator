# Relational generation method

Phase 1 reuses Great Generator's existing acyclic parent-first Pandas generation. Coverage witnesses
are allocated after baseline generation:

1. each scenario receives a distinct row position in every referenced table;
2. predicate assignments are written only to those witness rows;
3. declared FK-to-PK joins copy the selected parent key into the child FK;
4. undeclared equality joins prefer the primary-key side when one is identifiable;
5. validation rechecks PK uniqueness, unique constraints, simple/composite FK tuples, and witness
   join equality.

This phase does not claim generic composite-key generation, self-reference, cyclic dependency, or
cardinality-profile support. The schema model can represent some of these structures, but the
generic execution path is not yet complete.
