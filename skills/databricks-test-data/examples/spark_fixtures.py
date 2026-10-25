"""Call in an existing Spark session. Importing this file never creates a session or writes."""

from __future__ import annotations

import runpy
import sys
from datetime import date
from importlib.metadata import version
from pathlib import Path

from great_generator import generate_from_schema, generate_history, generate_relational, parse_ddl
from great_generator.io.manifest import build_generation_manifest


def helpers():
    return runpy.run_path(str(Path(__file__).parents[1] / "scripts/spark_checks.py"))


def runtime_context(spark):
    return {
        "python": sys.version,
        "date_context": date.today().isoformat(),
        "packages": {p: version(p) for p in ("great-generator", "pandas", "numpy", "faker")},
        "spark": spark.version,
        "spark_timezone": spark.conf.get("spark.sql.session.timeZone"),
    }


def structtype_fixture(spark, rows=1000, seed=42):
    from pyspark.sql.types import IntegerType, StringType, StructField, StructType

    if not 0 < rows <= 100000:
        raise ValueError(
            "This local-backed example is capped at 100000 rows; review driver memory."
        )
    schema = StructType(
        [
            StructField("customer_id", IntegerType(), False),
            StructField("customer_name", StringType(), True),
        ]
    )
    df = generate_from_schema(schema, rows=rows, engine="spark", spark=spark, seed=seed)
    report = helpers()["check_spark_keys"](
        {"customers": df}, primary_keys={"customers": "customer_id"}
    )
    report["passed"] = report["passed"] and report["row_counts"]["customers"] == rows
    manifest = build_generation_manifest(
        dataset_name="spark_schema_fixture",
        tables={"customers": df},
        engine="spark",
        seed=seed,
        parameters={"schema": schema.json(), "rows": rows, "runtime": runtime_context(spark)},
        validation=report,
        warnings=[
            "Generic schema generation builds Pandas data on the driver before Spark conversion."
        ],
    )
    if not report["passed"]:
        raise ValueError(f"Spark fixture validation failed: {report}")
    return df, manifest


def ddl_relational_fixture(spark, seed=42):
    ddl = """
    CREATE TABLE customers (customer_id INT PRIMARY KEY, customer_name STRING);
    CREATE TABLE orders (order_id INT PRIMARY KEY,
        customer_id INT NOT NULL REFERENCES customers(customer_id), amount DOUBLE);
    """
    contract = parse_ddl(ddl, dialect="databricks")
    tables = {
        name: {"schema": schema, "rows": 12 if name == "customers" else 48}
        for name, schema in contract.tables.items()
    }
    data = generate_relational(
        tables,
        relationships=["orders.customer_id -> customers.customer_id"],
        engine="spark",
        spark=spark,
        seed=seed,
    )
    report = helpers()["check_spark_keys"](
        data,
        primary_keys={"customers": "customer_id", "orders": "order_id"},
        relationships=[("orders", "customer_id", "customers", "customer_id")],
        non_nullable=[("orders", "customer_id")],
    )
    report["passed"] = report["passed"] and report["row_counts"] == {"customers": 12, "orders": 48}
    if not report["passed"]:
        raise ValueError(f"Spark relational checks failed: {report}")
    manifest = build_generation_manifest(
        dataset_name="spark_relational_fixture",
        tables=data,
        engine="spark",
        seed=seed,
        schema_fingerprint=contract.fingerprint(),
        parameters={
            "ddl": ddl,
            "rows": {"customers": 12, "orders": 48},
            "relationships": ["orders.customer_id -> customers.customer_id"],
            "runtime": runtime_context(spark),
        },
        validation=report,
        warnings=["Spark relational values differ from Pandas semantic generation."],
    )
    return data, manifest


def scd2_fixture(spark, seed=42):
    """Small domain history, converted to Spark and checked with distributed expressions."""
    from pyspark.sql import Window
    from pyspark.sql import functions as F

    history = generate_history("banking", "customers", scale="tiny", seed=seed)
    df = spark.createDataFrame(history)
    order = Window.partitionBy("customer_id").orderBy("effective_from", "effective_to")
    intervals = df.withColumn("previous_to", F.lag("effective_to").over(order))
    current = df.groupBy("customer_id").agg(
        F.sum(F.col("is_current").cast("int")).alias("current_count"),
        F.max("effective_from").alias("last_start"),
        F.max(F.when(F.col("is_current"), F.col("effective_from"))).alias("current_start"),
    )
    report = helpers()["check_spark_keys"](
        {"history": df},
        primary_keys={"history": "scd_id"},
        non_nullable=[
            ("history", name)
            for name in ("customer_id", "effective_from", "effective_to", "is_current")
        ],
    )
    report["checks"].update(
        {
            "positive_intervals": df.filter(F.col("effective_from") >= F.col("effective_to"))
            .limit(1)
            .count()
            == 0,
            "no_overlap": intervals.filter(F.col("effective_from") < F.col("previous_to"))
            .limit(1)
            .count()
            == 0,
            "one_current_latest": current.filter(
                (F.col("current_count") != 1) | (F.col("current_start") != F.col("last_start"))
            )
            .limit(1)
            .count()
            == 0,
        }
    )
    report["passed"] = all(report["checks"].values()) and report["row_counts"]["history"] > 0
    if not report["passed"]:
        raise ValueError(f"SCD2 fixture failed validation: {report}")
    manifest = build_generation_manifest(
        dataset_name="spark_scd2",
        tables={"history": df},
        engine="spark",
        seed=seed,
        parameters={
            "domain": "banking",
            "table": "customers",
            "scale": "tiny",
            "history_window": "2y",
            "runtime": runtime_context(spark),
        },
        validation=report,
        warnings=["Domain history is generated in Pandas before Spark conversion."],
    )
    return df, manifest
