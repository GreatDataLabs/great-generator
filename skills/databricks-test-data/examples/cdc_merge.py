"""Prepare ONE independent CDC case per key; not a production event-replay implementation."""

from __future__ import annotations

import json

import pandas as pd

from great_generator import generate_cdc


def prepare_merge_case(events):
    """Return initial and expected snapshots, plus a unique-key MERGE source.

    Drop labeled duplicates and select the highest sequence per key by an explicit
    example policy. Sequence is not event time. Build the target from those selected
    events' before images, so insert/update/delete preconditions are actually true.
    Never use this helper to reconstruct a real source system's history.
    """
    required = {"customer_id", "operation", "before", "after", "sequence_number", "duplicate"}
    if not required.issubset(events.columns):
        raise ValueError(f"Missing CDC columns: {sorted(required - set(events.columns))}")
    if events[list(required - {"before", "after"})].isna().any().any():
        raise ValueError("CDC identifiers, operation, sequence and duplicate flag cannot be null.")
    if not events.duplicate.isin([True, False]).all():
        raise ValueError("duplicate must contain boolean flags.")
    if not pd.api.types.is_integer_dtype(events.customer_id.dtype):
        raise ValueError("This banking example requires integer customer_id values.")
    if (
        not pd.api.types.is_integer_dtype(events.sequence_number.dtype)
        or not events.sequence_number.gt(0).all()
    ):
        raise ValueError("sequence_number must contain positive integers.")
    clean = events.loc[~events.duplicate.astype(bool)].copy()
    if not clean.operation.isin(["insert", "update", "delete"]).all():
        raise ValueError("Unsupported CDC operation.")
    if not clean.sequence_number.is_unique:
        raise ValueError("Ambiguous sequence numbers; provide an explicit ordering policy.")
    chosen = clean.sort_values("sequence_number", kind="stable").drop_duplicates(
        "customer_id", keep="last"
    )
    initial, expected, source = [], [], []

    def payload(value, key):
        if not isinstance(value, str):
            raise ValueError("Required CDC images must be JSON strings.")
        try:
            record = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid CDC JSON image.") from exc
        if not isinstance(record, dict) or record.get("customer_id") != key:
            raise ValueError("CDC payload key does not match envelope key.")
        if not isinstance(record.get("status"), str):
            raise ValueError("This projected CDC example requires a string status.")
        return {"customer_id": int(key), "status": str(record["status"])}

    for event in chosen.itertuples(index=False):
        if event.operation == "insert" and pd.notna(event.before):
            raise ValueError("Insert events must not have a before image.")
        if event.operation == "delete" and pd.notna(event.after):
            raise ValueError("Delete events must not have an after image.")
        before = payload(event.before, event.customer_id) if event.operation != "insert" else None
        after = payload(event.after, event.customer_id) if event.operation != "delete" else None
        if before is not None:
            initial.append(before)
        if after is not None:
            expected.append(after)
        source.append({**(after or before), "operation": event.operation})
    return (
        pd.DataFrame(initial, columns=["customer_id", "status"]),
        pd.DataFrame(source, columns=["customer_id", "status", "operation"]),
        pd.DataFrame(expected, columns=["customer_id", "status"]),
    )


def build_case(seed=42):
    events = generate_cdc("banking", "customers", rows=60, seed=seed, duplicate_rate=0.05)
    return prepare_merge_case(events)


def merge_into_test_table(spark, source, target, *, approved_target=None):
    """Explicit opt-in update/delete of an existing disposable Delta test table."""
    import runpy
    from pathlib import Path

    safety = runpy.run_path(str(Path(__file__).parents[1] / "scripts/safe_delta.py"))
    safety["validate_target"](target, "table")
    if approved_target != target:
        raise ValueError(
            "MERGE changes and deletes target rows; confirm the exact test table first."
        )
    if source.empty or source.customer_id.isna().any() or not source.customer_id.is_unique:
        raise ValueError(
            "MERGE source must have non-null unique customer_id values and be non-empty."
        )
    if not source.operation.isin(["insert", "update", "delete"]).all():
        raise ValueError("Unsupported CDC operation.")
    from delta.tables import DeltaTable

    source_df = spark.createDataFrame(
        source.to_dict("records"), "customer_id long, status string, operation string"
    )
    destination = DeltaTable.forName(spark, target)
    target_df = destination.toDF()
    checks = runpy.run_path(str(Path(__file__).parents[1] / "scripts/spark_checks.py"))
    if not checks["check_spark_keys"](
        {"target": target_df}, primary_keys={"target": "customer_id"}
    )["passed"]:
        raise ValueError("Target must have non-null unique customer_id values before MERGE.")
    (
        destination.alias("t")
        .merge(source_df.alias("s"), "t.customer_id = s.customer_id")
        .whenMatchedDelete(condition="s.operation = 'delete'")
        .whenMatchedUpdate(condition="s.operation = 'update'", set={"status": "s.status"})
        .whenNotMatchedInsert(
            condition="s.operation = 'insert'",
            values={"customer_id": "s.customer_id", "status": "s.status"},
        )
        .execute()
    )


if __name__ == "__main__":
    initial, source, expected = build_case()
    print(
        {"initial_rows": len(initial), "source_rows": len(source), "expected_rows": len(expected)}
    )
    print("No Spark session created and no table written. Review the prepared case before MERGE.")
