# Research limitations

- Phase 1 supports a bounded SQL SELECT subset and Pandas execution.
- OR and NOT are represented, but combined witness guarantees currently target conjunctive filters.
- HAVING, CTEs, windows, subqueries, computed predicates, LIKE, and dialect-specific semantics are
  diagnostics rather than full scenario plans.
- Expected assertions cover bounded witness truth, not arbitrary full-query equivalence.
- Generic composite-key materialization, cyclic graphs, and self-references remain incomplete.
- Spark-native workload witnesses and temporal fact-to-SCD2 lookups are not implemented.
- The first mutation result is one deterministic local fixture and does not establish generality.
- Commercial products have not been independently benchmarked.
- Coverage percentages apply only to the report's explicit supported denominator.
