# Formal coverage model

Let a parsed query contain atomic predicates `P = {p1, ..., pn}`, extracted joins `J`, and
eligible boundary predicates `B`.

For predicate `pi`, the Phase 1 target state set is:

```text
Ti = {TRUE, FALSE} union {UNKNOWN when the referenced column is nullable and NULL coverage is requested}
```

Measured predicate-state coverage is:

```text
sum_i |validated_states(pi) intersect Ti| / sum_i |Ti|
```

Join-path coverage is:

```text
validated equality-join requirements / extracted supported equality-join requirements
```

Boundary coverage is:

```text
validated threshold requirements / extracted eligible threshold requirements
```

Negative-case coverage is:

```text
materialized labeled negative case types / requested supported negative case types
```

An empty denominator is reported as `null`, not 100%. Percentages apply only to this documented
subset; they are not complete SQL, branch, path, or mutation coverage.

The reference evaluator uses SQL three-valued logic:

- `FALSE AND x = FALSE`;
- `TRUE AND UNKNOWN = UNKNOWN`;
- `TRUE OR x = TRUE`;
- `FALSE OR UNKNOWN = UNKNOWN`;
- `NOT UNKNOWN = UNKNOWN`.
