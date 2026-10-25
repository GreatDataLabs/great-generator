# Determinism and Reproducibility

Great Generator is designed to make synthetic data generation repeatable when users provide the same inputs.

## What is deterministic

For the same library version, schema, row counts, seed, realism mode, generation plan, and arguments, generation should produce the same logical output.

This applies to:

- single-table `generate_from_schema(...)` calls
- relational `generate_relational(...)` calls
- parsed DDL contracts passed into `generate_from_schema(...)`
- domain generation with fixed `scale` or fixed `rows`
- CDC generation when event counts and rates are fixed
- deterministic business-rule examples, such as the retail star-schema demo

## When to pass a seed

`seed` is optional.

Use it when you need reproducible test fixtures, CI checks, tutorials, demos, research experiments, or benchmark comparisons.

```python
from great_generator import generate_from_schema

schema = "customer_id int, customer_name string, email string"

first = generate_from_schema(schema, rows=100, seed=42)
second = generate_from_schema(schema, rows=100, seed=42)

assert first.equals(second)
```

If you do not pass a seed, Great Generator can still create useful synthetic data, but exact values may vary between runs.

## What can change output

Output can change when you change:

- package version
- schema or DDL
- row counts
- seed
- realism mode
- custom rules
- advisor plan
- domain pack behavior
- optional anomaly settings
- engine-specific execution path
- dependency/runtime versions, timezone and current date for semantic fields that use today's date

For long-lived experiments, record these inputs in a manifest. Pin explicit date windows
where supported and retain date context: a fixed seed alone does not freeze every
time-derived semantic default across calendar dates.

## Spark note

Spark DataFrames are distributed. Row content can be deterministic, but physical file layout, partition order, and row order after distributed operations may vary unless users explicitly sort or repartition.

For small, explicitly bounded Spark comparisons only:

```python
actual = df.orderBy("id").toPandas()
```

For larger datasets, compare by primary keys and columns using distributed joins or
two-way `exceptAll` checks instead of collecting to the driver or relying on physical
file order. Validation actions have compute cost even when no rows are collected.

## Recommended reproducibility checklist

- Pin the package version.
- Save the schema or DDL contract.
- Save row counts and generation arguments.
- Pass an explicit seed.
- Record the engine and runtime.
- Save a generation manifest.
- Validate keys and expected business rules after generation.
