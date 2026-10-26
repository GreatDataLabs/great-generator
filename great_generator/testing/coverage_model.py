"""Three-valued predicate evaluation for bounded coverage witnesses."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd

from great_generator.testing.query_contract import (
    BooleanExpression,
    PredicateRequirement,
)

TRUE = "TRUE"
FALSE = "FALSE"
UNKNOWN = "UNKNOWN"


def evaluate_predicate(requirement: PredicateRequirement, value: Any) -> str:
    """Evaluate one supported predicate using SQL-style NULL semantics."""

    operator = requirement.operator.upper()
    if operator == "IS NULL":
        return TRUE if _is_null(value) else FALSE
    if operator == "IS NOT NULL":
        return FALSE if _is_null(value) else TRUE
    if _is_null(value):
        return UNKNOWN

    expected = tuple(_comparable(item, value) for item in requirement.values)
    actual = _comparable(value, requirement.values[0] if requirement.values else value)
    if operator == "=":
        return TRUE if actual == expected[0] else FALSE
    if operator in {"!=", "<>"}:
        return TRUE if actual != expected[0] else FALSE
    if operator == ">":
        return TRUE if actual > expected[0] else FALSE
    if operator == ">=":
        return TRUE if actual >= expected[0] else FALSE
    if operator == "<":
        return TRUE if actual < expected[0] else FALSE
    if operator == "<=":
        return TRUE if actual <= expected[0] else FALSE
    if operator == "IN":
        return TRUE if actual in expected else FALSE
    if operator == "NOT IN":
        return FALSE if actual in expected else TRUE
    if operator == "BETWEEN":
        return TRUE if expected[0] <= actual <= expected[1] else FALSE
    if operator == "NOT BETWEEN":
        return FALSE if expected[0] <= actual <= expected[1] else TRUE
    raise ValueError(f"Unsupported predicate operator '{requirement.operator}'.")


def evaluate_boolean_expression(
    expression: BooleanExpression | None,
    predicate_states: dict[str, str],
) -> str:
    """Evaluate a normalized boolean tree using SQL three-valued logic."""

    if expression is None:
        return TRUE
    if expression.kind == "predicate":
        return predicate_states.get(str(expression.predicate_id), UNKNOWN)
    if expression.kind == "unsupported":
        return UNKNOWN
    children = [
        evaluate_boolean_expression(child, predicate_states) for child in expression.children
    ]
    if expression.kind == "not":
        if not children:
            return UNKNOWN
        return {TRUE: FALSE, FALSE: TRUE, UNKNOWN: UNKNOWN}[children[0]]
    if expression.kind == "and":
        if FALSE in children:
            return FALSE
        if UNKNOWN in children:
            return UNKNOWN
        return TRUE
    if expression.kind == "or":
        if TRUE in children:
            return TRUE
        if UNKNOWN in children:
            return UNKNOWN
        return FALSE
    return UNKNOWN


def _is_null(value: Any) -> bool:
    if value is None or value is pd.NA:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _comparable(value: Any, reference: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        value = value.to_pydatetime()
    if isinstance(reference, pd.Timestamp):
        reference = reference.to_pydatetime()
    if isinstance(reference, datetime) and isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    if (
        isinstance(reference, date)
        and not isinstance(reference, datetime)
        and isinstance(value, str)
    ):
        return date.fromisoformat(value[:10])
    return value
