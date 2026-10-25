"""Local Spark checks. These do not certify Databricks, Unity Catalog or Delta writes."""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "skills/databricks-test-data"


@pytest.fixture(scope="module")
def spark():
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)
    pyspark = pytest.importorskip("pyspark")
    session = (
        pyspark.sql.SparkSession.builder.master("local[1]")
        .appName("great-generator-skills")
        .getOrCreate()
    )
    session.conf.set("spark.sql.shuffle.partitions", "2")
    return session


@pytest.mark.parametrize(
    "function", ["structtype_fixture", "ddl_relational_fixture", "scd2_fixture"]
)
def test_spark_fixtures_validate_without_collecting_tables(spark, function, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Skill validation must not collect full Spark tables to the driver.")

    # Spark 4 returns a concrete subclass; patch that rather than only its base API.
    frame_type = type(spark.range(1))
    monkeypatch.setattr(frame_type, "collect", forbidden)
    monkeypatch.setattr(frame_type, "toPandas", forbidden)
    example = runpy.run_path(str(ROOT / "examples/spark_fixtures.py"))
    _, manifest = example[function](spark)
    assert manifest["validation"]["passed"]
    assert manifest["validation"]["row_counts"]


def test_spark_checker_detects_invalid_keys(spark):
    check = runpy.run_path(str(ROOT / "scripts/spark_checks.py"))["check_spark_keys"]
    tables = {
        "parent": spark.createDataFrame([(1,), (1,)], "id int"),
        "child": spark.createDataFrame([(1, 9), (2, None)], "id int, pid int"),
    }
    report = check(
        tables,
        primary_keys={"parent": "id", "child": "id"},
        relationships=[("child", "pid", "parent", "id")],
        non_nullable=[("child", "pid")],
    )
    assert not report["passed"]
    assert not report["checks"]["parent.id:unique"]
    assert not report["checks"]["child.pid->parent.id:fk"]
    assert not report["checks"]["child.pid:required"]
