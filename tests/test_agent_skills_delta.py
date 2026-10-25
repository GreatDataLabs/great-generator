"""Explicit opt-in Databricks/Delta integration; leaves a disposable table for inspection."""

from __future__ import annotations

import os
import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "skills/databricks-test-data"


@pytest.mark.skipif(
    os.environ.get("GG_RUN_DELTA_SKILL_TESTS") != "1",
    reason="Needs explicit opt-in, an active Delta session and a new test target.",
)
def test_delta_case_matches_expected_snapshot_in_approved_runtime():
    from pyspark.sql import SparkSession

    target = os.environ.get("GG_DELTA_SKILL_TARGET", "")
    assert target, "Set GG_DELTA_SKILL_TARGET to an authorized, unused catalog.schema.table."
    spark = SparkSession.getActiveSession()
    assert spark is not None, "Run pytest.main in the authorized notebook's Python session."
    safety = runpy.run_path(str(ROOT / "scripts/safe_delta.py"))
    case = runpy.run_path(str(ROOT / "examples/cdc_merge.py"))
    initial, source, expected = case["build_case"]()
    assert set(source.operation) == {"insert", "update", "delete"}
    initial_df = spark.createDataFrame(
        initial.to_dict("records"), "customer_id long, status string"
    )
    # If the target already exists this must fail, not reset it.
    safety["write_delta"](initial_df, target, approved_target=target)
    case["merge_into_test_table"](spark, source, target, approved_target=target)
    actual = spark.table(target).select("customer_id", "status")
    wanted = spark.createDataFrame(expected.to_dict("records"), "customer_id long, status string")
    assert actual.exceptAll(wanted).count() == 0
    assert wanted.exceptAll(actual).count() == 0
    assert actual.count() == len(expected)
