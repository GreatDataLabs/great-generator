"""Bounded scenario pack; deliberate mutations are labeled fixture construction."""

from __future__ import annotations

import json
import runpy
import sys
from datetime import date
from importlib.metadata import version
from pathlib import Path

import pandas as pd

from great_generator import (
    generate_cdc,
    generate_from_schema,
    generate_history,
    generate_relational,
)
from great_generator.io.manifest import build_generation_manifest


def build_pack(seed=42, *, include_anomalies=False):
    """Return frames, scenario assertions and a manifest. No writes or model calls."""
    happy = generate_from_schema(
        "customer_id int, customer_name string, balance double, signup_date date",
        rows=12,
        seed=seed,
        custom_rules={
            "balance": {"min": 0, "max": 100},
            "signup_date": {"start": "2026-01-01", "end": "2026-01-31"},
        },
    )
    boundary = happy.head(2).copy()
    # Explicit test scenario transformation, not a promise that random sampling hits endpoints.
    boundary["balance"] = [0.0, 100.0]
    boundary["signup_date"] = pd.to_datetime(["2026-01-01", "2026-01-31"])
    changed = happy.iloc[[0]].copy()
    changed["customer_name"] = "Synthetic Changed Customer"
    unchanged = happy.iloc[[1]].copy()
    new_entity = happy.iloc[[2]].copy()
    new_entity["customer_id"] = int(happy.customer_id.max()) + 1
    history = generate_history("banking", "customers", scale="tiny", seed=seed)
    check_history = runpy.run_path(str(Path(__file__).parents[1] / "scripts/check_history.py"))[
        "check_history"
    ]
    history_report = check_history(history, "customer_id")
    related = generate_relational(
        {
            "parent": {"schema": "id int primary key", "rows": 4},
            "child": {
                "schema": "id int primary key, parent_id int references parent.id",
                "rows": 16,
            },
        },
        seed=seed,
    )
    data = {
        "happy": happy,
        "boundary": boundary,
        "changed": changed,
        "unchanged": unchanged,
        "new_entity": new_entity,
        "history": history,
        **related,
    }
    scenarios = {
        "happy": {"passed": len(happy) == 12 and happy.balance.between(0, 100).all()},
        "boundaries": {
            "passed": boundary.balance.tolist() == [0.0, 100.0]
            and boundary.signup_date.dt.strftime("%Y-%m-%d").tolist()
            == ["2026-01-01", "2026-01-31"]
        },
        "changed": {
            "passed": changed.customer_id.iloc[0] == happy.customer_id.iloc[0]
            and changed.customer_name.iloc[0] != happy.customer_name.iloc[0]
        },
        "unchanged": {"passed": unchanged.equals(happy.iloc[[1]])},
        "new_entity": {"passed": not new_entity.customer_id.isin(happy.customer_id).any()},
        "history": history_report,
        "relationships": {
            "passed": related["parent"].id.is_unique
            and related["child"].id.is_unique
            and related["child"].parent_id.isin(related["parent"].id).all()
        },
    }
    for operation in ("insert", "update", "delete"):
        events = generate_cdc("banking", "customers", rows=12, operations=[operation], seed=seed)
        data[f"cdc_{operation}"] = events
        before_ok = (
            events.before.isna().all() if operation == "insert" else events.before.notna().all()
        )
        after_ok = (
            events.after.isna().all() if operation == "delete" else events.after.notna().all()
        )
        scenarios[f"cdc_{operation}"] = {
            "passed": events.operation.eq(operation).all()
            and before_ok
            and after_ok
            and events.ingestion_timestamp.ge(events.event_timestamp).all()
        }
    if include_anomalies:
        bad = happy.head(3).copy()
        bad.loc[bad.index[0], "customer_name"] = None
        bad.loc[bad.index[1], "balance"] = -1.0
        bad = pd.concat([bad, bad.iloc[[2]]], ignore_index=True)
        data["deliberately_invalid"] = bad
        scenarios["explicit_anomalies"] = {
            "passed": bad.customer_name.isna().sum() == 1
            and bad.balance.lt(0).sum() == 1
            and bad.duplicated().sum() == 1,
            "expected_validation_failures": ["null name", "negative balance", "duplicate row"],
        }
    for entry in scenarios.values():
        entry["passed"] = bool(entry["passed"])
    manifest = build_generation_manifest(
        dataset_name="pipeline_pack",
        tables=data,
        seed=seed,
        parameters={
            "example": "pipeline_pack.py",
            "include_anomalies": include_anomalies,
            "python": sys.version,
            "date_context": date.today().isoformat(),
            "packages": {p: version(p) for p in ("great-generator", "pandas", "numpy", "faker")},
        },
        validation={
            "passed": all(item["passed"] for item in scenarios.values()),
            "scenarios": scenarios,
        },
        warnings=[
            "Comparison batches are deterministic example transformations, not core SCD scenario APIs.",
            "CDC examples are independent events, not a coherent replay log.",
            "Pipeline execution and downstream acceptance are not tested by this fixture pack.",
        ],
    )
    if not manifest["validation"]["passed"]:
        raise ValueError(f"Scenario checks failed: {scenarios}")
    return data, manifest


if __name__ == "__main__":
    _, manifest = build_pack()
    print(json.dumps(manifest, indent=2, default=str))
