# Query-Aware Generation

Query-aware generation lets users create synthetic data that contains the values, partition dates, and join paths needed by their SQL queries.

It is useful when you need safe, non-production data for SQL logic tests, ETL validation, partition pruning checks, join testing, aggregation demos, and environment-specific performance experiments.

All query-aware options are optional. Existing generation behavior is unchanged unless you provide `required_values`, `partition_by`, `target_selectivity`, `ensure_join_coverage`, or `query_profile`.

## End-to-end single-table example

```python
from great_generator import generate_from_schema, validate_query_coverage

schema = """
member_id string,
business_date date,
region string,
product_type string,
member_status string,
interaction_count int,
balance double
"""

required_values = {
    "region": ["SOUTH"],
    "product_type": ["CHECKING", "SAVINGS"],
    "member_status": ["ACTIVE"],
}

partition_by = {
    "column": "business_date",
    "values": ["2026-01-01", "2026-01-02", "2026-01-03"],
    "distribution": "balanced",
}

df = generate_from_schema(
    schema=schema,
    rows=100000,
    required_values=required_values,
    partition_by=partition_by,
)

report = validate_query_coverage(
    data=df,
    required_values=required_values,
    partition_by=partition_by,
)
```

Coverage reports include:

- `required_values_status`
- `partition_coverage_status`
- `partition_counts`
- `selectivity_actuals`
- `selectivity_targets`
- `join_coverage_status`
- `warnings`

## What query-aware generation does

Query-aware generation can:

- ensure filter values appear in generated columns
- include specific partition dates or partition keys
- distribute rows evenly across partition values
- support custom row counts per partition
- approximate requested value selectivity
- ensure relational fact rows join to required dimension values
- produce a coverage report for generated data

## When to use it

Use query-aware generation when you have a query such as:

```sql
SELECT region, product_type, SUM(interaction_count)
FROM fact_interaction f
JOIN dim_member m ON f.member_id = m.member_id
JOIN dim_product p ON f.product_id = p.product_id
WHERE f.business_date IN ('2026-01-01', '2026-01-02')
  AND m.region = 'SOUTH'
  AND p.product_type IN ('CHECKING', 'SAVINGS')
GROUP BY region, product_type;
```

and you need generated data that actually contains:

- `region = 'SOUTH'`
- `product_type IN ('CHECKING', 'SAVINGS')`
- the requested `business_date` partitions
- fact rows that join to matching member and product dimension rows

## What it does not guarantee

Query-aware generation helps synthetic data match expected query values, partition dates, and join paths. It does not guarantee identical production performance because file layout, table statistics, clustering, caching, concurrency, warehouse size, and query engine configuration also affect runtime.

For performance testing, record your environment and validate results in the target runtime.

## Single-table required values

```python
from great_generator import generate_from_schema

schema = """
member_id string,
business_date date,
region string,
product_type string,
member_status string,
interaction_count int,
balance double
"""

df = generate_from_schema(
    schema=schema,
    rows=100_000,
    required_values={
        "region": ["SOUTH"],
        "product_type": ["CHECKING", "SAVINGS"],
        "member_status": ["ACTIVE"],
    },
)
```

`required_values` ensures the listed values appear. It does not make the column contain only those values.

## Partition-aware generation

Balanced partitions:

```python
df = generate_from_schema(
    schema=schema,
    rows=90_000,
    partition_by={
        "column": "business_date",
        "values": ["2026-01-01", "2026-01-02", "2026-01-03"],
        "distribution": "balanced",
    },
)
```

Custom counts:

```python
df = generate_from_schema(
    schema=schema,
    rows=295_000,
    partition_by={
        "column": "business_date",
        "counts": {
            "2026-01-01": 100_000,
            "2026-01-02": 100_000,
            "2026-01-03": 95_000,
        },
    },
)
```

For custom counts, the sum of `counts` must match `rows`. Great Generator raises a validation error instead of silently changing the row count.

## Target selectivity

```python
df = generate_from_schema(
    schema=schema,
    rows=100_000,
    target_selectivity={
        "region": {"SOUTH": 0.25},
        "product_type": {
            "CHECKING": 0.30,
            "SAVINGS": 0.20,
        },
        "member_status": {"ACTIVE": 0.80},
    },
)
```

Selectivity is approximate. For example, `0.25` means Great Generator will attempt to make about 25% of rows match that value.

If `target_selectivity` is provided without `required_values`, the selectivity keys are treated as required values.

## Relational join coverage

```python
from great_generator import generate_relational

data = generate_relational(
    tables={
        "dim_member": {
            "schema": "member_id int primary key, region string, member_status string",
            "rows": 100_000,
        },
        "dim_product": {
            "schema": "product_id int primary key, product_type string",
            "rows": 1_000,
        },
        "fact_interaction": {
            "schema": (
                "interaction_id int primary key, "
                "member_id int references dim_member.member_id, "
                "product_id int references dim_product.product_id, "
                "business_date date, interaction_count int"
            ),
            "rows": 1_000_000,
        },
    },
    required_values={
        "dim_member.region": ["SOUTH"],
        "dim_member.member_status": ["ACTIVE"],
        "dim_product.product_type": ["CHECKING", "SAVINGS"],
    },
    partition_by={
        "table": "fact_interaction",
        "column": "business_date",
        "values": ["2026-01-01", "2026-01-02", "2026-01-03"],
        "distribution": "balanced",
    },
    ensure_join_coverage=True,
)
```

When `ensure_join_coverage=True`, Great Generator ensures child rows reference parent rows that contain the required dimension values.

For relational generation, query-aware `partition_by` uses a mapping with `table` and `column`. Existing export partitioning still accepts a list of columns when writing output.

## Query profile

Direct arguments are recommended for simple use. Advanced users can reuse a profile dictionary:

```python
profile = {
    "required_values": {
        "region": ["SOUTH"],
        "product_type": ["CHECKING", "SAVINGS"],
    },
    "partition_by": {
        "column": "business_date",
        "values": ["2026-01-01", "2026-01-02"],
        "distribution": "balanced",
    },
    "target_selectivity": {
        "region": {"SOUTH": 0.25},
    },
}

df = generate_from_schema(schema, rows=100_000, query_profile=profile)
```

Direct arguments override matching values from `query_profile`.

## Coverage report

```python
from great_generator import validate_query_coverage

report = validate_query_coverage(
    data=df,
    required_values={
        "region": ["SOUTH"],
        "product_type": ["CHECKING", "SAVINGS"],
    },
    partition_by={
        "column": "business_date",
        "values": ["2026-01-01", "2026-01-02"],
    },
    target_selectivity={
        "region": {"SOUTH": 0.25},
    },
)
```

The report includes:

- `required_values_status`
- `partition_coverage_status`
- `partition_counts`
- `selectivity_actuals`
- `selectivity_targets`
- `join_coverage_status`
- `warnings`
- `passed`

## Limitations

- Query-aware generation currently applies to Pandas generation paths.
- Spark users can generate Pandas query-aware data for smaller examples, convert to Spark, or use the existing Spark generation path without query-aware options.
- Selectivity is approximate, not an exact statistical guarantee.
- Join coverage uses declared relationships; missing or ambiguous relationships raise clear errors.
- Query-aware generation does not parse SQL text in this release.

## Roadmap

Future improvements may include:

- infer query profiles from SQL text
- weighted partition distributions
- business-day-only partition generation
- weekend and month-end skew modes
- Spark-native query-aware generation
- exact selectivity mode
