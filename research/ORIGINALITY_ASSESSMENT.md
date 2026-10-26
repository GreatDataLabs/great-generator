# Originality assessment

## Established methods

Constraint-based test generation, SQL mutation testing, query-aware data generation, relational
synthetic data, structural SQL coverage, property-based testing, and solver-backed database-state
generation are established methods. XData, QAGrow, DOMINO, SQLancer, Hypothesis, SDV, dbldatagen,
GenRocket, and MOSTLY AI cover important parts of this space.

## Adaptations in Great Generator

- SQLGlot AST traversal adapts standard compiler practice.
- TRUE/FALSE/UNKNOWN witnesses adapt condition and boundary coverage ideas.
- Parent-first FK generation and deterministic seeds are standard data-generation techniques.
- Mutation detection by comparing a reference query with a mutant is established methodology.

## Potentially distinctive integration

The combination of Great Generator's lightweight schema adapters, enterprise metadata path,
DataFrame-first outputs, deterministic workload witnesses, and explicit coverage artifacts may be a
useful engineering contribution. Whether it is scientifically original or materially better than
prior approaches is unproven.

## Claims that require evidence

- better defect detection across representative workloads;
- fewer rows needed to expose defects;
- scalable native Spark witness generation;
- temporal consistency across facts, SCD2, and CDC;
- practical independent adoption;
- meaningful differences from commercial by-design test-data systems.

No "first", "only", field-leading, or major-significance claim is currently substantiated.
