"""Check SCD2 interval invariants without inferring business change semantics."""

from __future__ import annotations

import pandas as pd


def check_history(frame, natural_key):
    required = [natural_key, "scd_id", "effective_from", "effective_to", "is_current"]
    if any(name not in frame for name in required):
        raise ValueError(f"History requires columns {required}")
    checks = {
        "non_empty": not frame.empty,
        "required_non_null": not frame[required].isna().any().any(),
        "surrogate_unique": frame.scd_id.is_unique,
        "boolean_current": frame.is_current.isin([True, False]).all(),
    }
    ordered = frame.sort_values([natural_key, "effective_from", "effective_to"])
    start = pd.to_datetime(ordered.effective_from, errors="raise")
    end = pd.to_datetime(ordered.effective_to, errors="raise")
    checks["positive_intervals"] = start.lt(end).all()
    previous_end = end.groupby(ordered[natural_key]).shift()
    checks["no_overlap"] = (previous_end.isna() | start.ge(previous_end)).all()
    checks["one_current_per_key"] = ordered.groupby(natural_key).is_current.sum().eq(1).all()
    checks["current_is_latest"] = ordered.groupby(natural_key).tail(1).is_current.eq(True).all()
    checks = {name: bool(value) for name, value in checks.items()}
    return {"passed": all(checks.values()), "checks": checks}
