"""Materialize bounded coverage witnesses into generated Pandas datasets."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from typing import Any

import pandas as pd

from great_generator.schemas.models import DomainSchema, ForeignKey
from great_generator.testing.coverage_model import (
    evaluate_boolean_expression,
    evaluate_predicate,
)
from great_generator.testing.query_contract import CoverageScenario, QueryContract, WorkloadContract


def materialize_scenarios(
    data: dict[str, pd.DataFrame],
    schema: DomainSchema,
    workload: WorkloadContract,
    scenarios: list[CoverageScenario],
) -> tuple[dict[str, pd.DataFrame], list[CoverageScenario]]:
    """Apply scenario assignments to distinct witness rows without changing row counts."""

    result = {name: frame.copy(deep=True) for name, frame in data.items()}
    queries = {query.query_id: query for query in workload.queries}
    next_row: dict[str, int] = defaultdict(int)
    materialized: list[CoverageScenario] = []

    for scenario in scenarios:
        query = queries[scenario.query_id]
        bindings: dict[str, int] = {}
        for table_name in query.tables:
            if table_name not in result:
                raise ValueError(
                    f"Scenario '{scenario.scenario_id}' references missing table '{table_name}'."
                )
            position = next_row[table_name]
            if position >= len(result[table_name]):
                raise ValueError(
                    f"Table '{table_name}' needs at least {position + 1} rows for the requested "
                    "coverage scenarios. Increase rows or request fewer coverage targets."
                )
            bindings[table_name] = position
            next_row[table_name] += 1

        for qualified_name, value in scenario.assignments.items():
            table_name, column_name = qualified_name.split(".", 1)
            if table_name not in bindings:
                raise ValueError(
                    f"Scenario assignment '{qualified_name}' is outside query "
                    f"'{query.query_id}'."
                )
            _set_position(result[table_name], bindings[table_name], column_name, value)

        for join in query.joins:
            _enforce_join(result, schema, query, scenario, bindings, join.left, join.right)

        materialized.append(replace(scenario, row_bindings=bindings))
    return result, materialized


def validate_materialized_scenario(
    data: dict[str, pd.DataFrame],
    query: QueryContract,
    scenario: CoverageScenario,
) -> dict[str, Any]:
    """Validate one witness against actual generated cells and join values."""

    predicate_states: dict[str, str] = {}
    predicate_status: dict[str, bool] = {}
    for predicate in query.predicates:
        position = scenario.row_bindings[predicate.column.table]
        value = _get_position(data[predicate.column.table], position, predicate.column.column)
        state = evaluate_predicate(predicate, value)
        predicate_states[predicate.requirement_id] = state
        predicate_status[predicate.requirement_id] = (
            state == scenario.expected_predicates[predicate.requirement_id]
        )

    join_status: dict[str, bool] = {}
    for join in query.joins:
        left = _get_position(
            data[join.left.table], scenario.row_bindings[join.left.table], join.left.column
        )
        right = _get_position(
            data[join.right.table], scenario.row_bindings[join.right.table], join.right.column
        )
        join_status[join.requirement_id] = bool(
            not _is_null(left) and not _is_null(right) and _normalized(left) == _normalized(right)
        )

    outcome = evaluate_boolean_expression(query.boolean_expression, predicate_states)
    passed = (
        all(predicate_status.values())
        and all(join_status.values())
        and outcome == scenario.expected_query_outcome
    )
    return {
        "scenario_id": scenario.scenario_id,
        "query_id": scenario.query_id,
        "kind": scenario.kind,
        "predicate_states": predicate_states,
        "predicate_status": predicate_status,
        "join_status": join_status,
        "expected_query_outcome": scenario.expected_query_outcome,
        "actual_query_outcome": outcome,
        "passed": passed,
    }


def _enforce_join(
    data: dict[str, pd.DataFrame],
    schema: DomainSchema,
    query: QueryContract,
    scenario: CoverageScenario,
    bindings: dict[str, int],
    left: Any,
    right: Any,
) -> None:
    left_fk = _matching_fk(schema, left.table, left.column, right.table, right.column)
    right_fk = _matching_fk(schema, right.table, right.column, left.table, left.column)
    if left_fk is not None:
        _copy_join_value(data, bindings, parent=right, child=left, scenario=scenario)
        return
    if right_fk is not None:
        _copy_join_value(data, bindings, parent=left, child=right, scenario=scenario)
        return

    left_table = schema.tables[left.table]
    right_table = schema.tables[right.table]
    if right.column in right_table.primary_key_columns:
        _copy_join_value(data, bindings, parent=right, child=left, scenario=scenario)
    elif left.column in left_table.primary_key_columns:
        _copy_join_value(data, bindings, parent=left, child=right, scenario=scenario)
    else:
        left_value = _get_position(data[left.table], bindings[left.table], left.column)
        if _is_null(left_value):
            right_value = _get_position(data[right.table], bindings[right.table], right.column)
            _set_position(data[left.table], bindings[left.table], left.column, right_value)
        else:
            _set_position(data[right.table], bindings[right.table], right.column, left_value)


def _copy_join_value(
    data: dict[str, pd.DataFrame],
    bindings: dict[str, int],
    *,
    parent: Any,
    child: Any,
    scenario: CoverageScenario,
) -> None:
    child_name = child.qualified_name
    if child_name in scenario.assignments:
        requested = scenario.assignments[child_name]
        parent_frame = data[parent.table]
        matches = parent_frame[parent.column].map(_normalized) == _normalized(requested)
        positions = [index for index, value in enumerate(matches.tolist()) if value]
        if not positions:
            raise ValueError(
                f"Scenario '{scenario.scenario_id}' requires join-key value {requested!r} for "
                f"'{child_name}', but '{parent.qualified_name}' has no matching key."
            )
        bindings[parent.table] = positions[0]
        return
    value = _get_position(data[parent.table], bindings[parent.table], parent.column)
    _set_position(data[child.table], bindings[child.table], child.column, value)


def _matching_fk(
    schema: DomainSchema,
    child_table: str,
    child_column: str,
    parent_table: str,
    parent_column: str,
) -> ForeignKey | None:
    for foreign_key in schema.tables[child_table].foreign_keys:
        pairs = zip(foreign_key.child_columns, foreign_key.parent_columns)
        if foreign_key.parent_table == parent_table and any(
            child == child_column and parent == parent_column for child, parent in pairs
        ):
            return foreign_key
    return None


def _set_position(frame: pd.DataFrame, position: int, column: str, value: Any) -> None:
    if column not in frame.columns:
        raise ValueError(f"Scenario references unknown column '{column}'.")
    frame.iat[position, frame.columns.get_loc(column)] = value


def _get_position(frame: pd.DataFrame, position: int, column: str) -> Any:
    return frame.iat[position, frame.columns.get_loc(column)]


def _is_null(value: Any) -> bool:
    if value is None or value is pd.NA:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _normalized(value: Any) -> str:
    if _is_null(value):
        return "<NULL>"
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)
