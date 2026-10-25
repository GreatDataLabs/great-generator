# Databricks test data: schema to checked Spark fixtures

The [Databricks skill](../skills/databricks-test-data/SKILL.md) turns a request into
a reviewed generation plan, native PySpark outputs, explicit checks and optional
Delta delivery. It does not provision a cluster, discover Unity Catalog schemas
automatically or generate records with an LLM.

## Install and discover

In a notebook using a compatible Python runtime:

```python
%pip install great-generator
```

Use your workspace's normal restart/session procedure when required. Databricks
already supplies Spark; do not replace it unnecessarily. There is no
`great-generator[databricks]` extra. Pin a reviewed library version for reusable
fixtures. Keep the skill revision with your test project.

For Genie Code, place selected skill directories in your user
`/Users/{username}/.assistant/skills/` or an authorized workspace skills location.
Alternatively register the repository's parent `skills/` folder from a Databricks
Git folder in Genie Code settings. The parent contains the six skill subfolders;
do not register a SKILL.md file as the folder. Reload/start a new chat after updates.
These locations follow [Databricks' skill documentation](https://docs.databricks.com/aws/en/genie-code/skills);
workspace availability and permissions must be verified locally.

## Useful requests

- "Generate 100K rows for this StructType; first check whether it fits my driver."
- "Create test data from this Databricks CREATE TABLE statement."
- "Create CDC data to test my Delta MERGE, including the expected final snapshot."
- "Generate SCD2 history and new/changed/unchanged comparison cases."
- "Create PK/FK-consistent fixtures for new sandbox Delta tables."
- "Make this SQL query hit both product groups and show evidence."

## StructType and DataFrame schemas

```python
from pyspark.sql.types import LongType, StringType, StructField, StructType
from great_generator import generate_from_schema

schema = StructType([
    StructField("customer_id", LongType(), False),
    StructField("customer_name", StringType(), True),
    StructField("email", StringType(), True),
])
df = generate_from_schema(schema, rows=1000, engine="spark", seed=42)
# Also accepts an existing empty PySpark DataFrame or its schema.
# An explicit spark=spark is useful when no active session is discoverable.
```

**Important:** this generic path generates Pandas data on the driver before Spark
conversion. Returning a Spark DataFrame does not make the generation distributed.
Do not launch million/billion-row requests blindly. A bounded preview, measured
memory plan or a supported native relational/domain path may be appropriate, but
the latter has different semantics/rule support. No guaranteed throughput claim.

## Databricks DDL and related fixtures

```python
from great_generator import parse_ddl, generate_relational

contract = parse_ddl("""
CREATE TABLE customers (customer_id INT PRIMARY KEY, customer_name STRING);
CREATE TABLE orders (order_id INT PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(customer_id), amount DOUBLE);
""", dialect="databricks")

data = generate_relational(
    tables={
        "customers": {"schema": contract.tables["customers"], "rows": 100},
        "orders": {"schema": contract.tables["orders"], "rows": 400},
    },
    relationships=["orders.customer_id -> customers.customer_id"],
    engine="spark", seed=42,
)
customers, orders = data["customers"], data["orders"]
```

The explicit relationships argument is important for parsed TableSchema inputs.
DDL parsing does not execute CREATE TABLE, and not all parsed constraints are
generated/enforced. Composite/cyclic keys need a separately reviewed strategy.
Map qualified catalog names to simple fixture names explicitly when necessary.

For an existing UC table, use `inspect_unity_catalog_table(...)`,
`generate_from_unity_catalog(...)`, or
`generate_relational_from_unity_catalog(...)`. These APIs inspect permitted
information-schema metadata without sampling source rows, use bounded relationship
discovery, and delegate generation to the existing engines. See
[`DATABRICKS_UNITY_CATALOG.md`](DATABRICKS_UNITY_CATALOG.md). Catalog permissions,
runtime connectivity, and metadata completeness remain the user's responsibility.

## Validation before delivery

Run counts, declared PK uniqueness/null checks and FK left anti-joins. The example
[Spark checker](../skills/databricks-test-data/scripts/spark_checks.py) performs
distributed actions and returns checks plus counts; it does not collect the
dataset. Business rules, query branches and partition distributions need additional
Spark expressions. Generic semantic validation may skip Spark: that is **not run**.

[spark_fixtures.py](../skills/databricks-test-data/examples/spark_fixtures.py)
contains callable StructType, relational-DDL and SCD2 examples returning
`(df_or_tables, manifest)`. They do not create sessions or write on import.
From a checked-out Git folder, load the example with `runpy.run_path(path)` and
call the desired function with the notebook's `spark` object.

## Safe Delta and Unity Catalog output

Default to no write. Once the user approves an exact **new test target**, native
code can use:

```python
# Run only after approval and schema/permission checks:
# df.write.format("delta").mode("errorifexists").saveAsTable("sandbox.qa.customers_run_001")
```

The optional [safe writer example](../skills/databricks-test-data/scripts/safe_delta.py)
requires the approved target to match and rejects implicit overwrites. It does not
replace permissions or infer approval from a sandbox-looking name.

Managed table writes use `catalog.schema.table`. External/cloud/Volume paths write
files, not an automatically registered UC table. External registration is separate.
Cloud identity/connectors/storage permissions belong to the workspace. No tokens
in notebooks or manifests. Do not enable mergeSchema/overwriteSchema to hide an
incompatible contract. Append may create duplicates; overwrite replaces data;
partitioning may create many small files. Review each deliberately.

## CDC and SCD2 cases

The [CDC example](../skills/databricks-test-data/examples/cdc_merge.py) calls existing
banking/customer CDC generation, prepares independent unique-key cases, derives
an initial and expected snapshot, and provides an explicitly invoked Delta MERGE.
It does not treat random repeated events as a coherent history. Sequence and event
time are different. The [Delta MERGE guide](https://docs.databricks.com/aws/en/delta/merge)
explains why multiple matching source rows need careful preprocessing.

After writing a new initial snapshot and applying the approved MERGE, compare
actual versus expected using two-way `exceptAll` and row counts. Do not report an
end-to-end pass based only on Python fixture tests.

`generate_history` creates local domain history. The Spark example checks surrogate
keys, half-open intervals, no overlaps and one latest/current version per entity.
The natural key repeats intentionally. The pipeline skill provides explicit
new/changed/unchanged batches; these are example transformations, not a new core
API or a general SCD2 MERGE implementation.

For Bronze/Silver/Gold tests, generate source cases and expected assertions, then
run the user's pipeline separately. Query-aware options remain Pandas-only: generate
a small bounded fixture and convert deliberately, or report the native Spark gap.

## Provenance

Record schema/contract hash, relationships, counts, rules, seed, package and runtime,
timezone/date context and validation. The existing manifest builder avoids implicit
Spark counts; provide the checker counts in `validation`. It is not a data checksum.
Some semantic defaults use today's date; fix date windows and context where needed.

## Tests and honest environment boundaries

Local tests exercise Spark generation/checks without full-table collect, and mock
writer calls to verify modes and targets. They do **not** certify a Databricks workspace.

An optional end-to-end test is supplied for an authorized notebook Python session:

```python
# This creates a NEW disposable Delta table and updates/deletes its rows.
# Set only after approving the exact unused test target and reviewing the test.
# import os, pytest
# os.environ["GG_RUN_DELTA_SKILL_TESTS"] = "1"
# os.environ["GG_DELTA_SKILL_TARGET"] = "sandbox.qa.gg_cdc_run_001"
# pytest.main(["tests/test_agent_skills_delta.py", "-q"])
```

It requires an active compatible Spark/Delta session and schema permissions. An
existing target causes failure, never an automatic reset. The test leaves the table
for inspection; cleanup is a separate explicit decision. This test is skipped by
default and never contacts a workspace from CI automatically.
