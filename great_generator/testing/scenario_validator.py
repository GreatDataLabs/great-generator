"""Validation for clean contract-to-test datasets and coverage witnesses."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from great_generator.schemas.models import DomainSchema
from great_generator.testing.query_contract import CoverageScenario, WorkloadContract
from great_generator.testing.scenario_generator import validate_materialized_scenario


def validate_test_dataset(
    data: Mapping[str, pd.DataFrame],
    schema: DomainSchema,
    row_counts: Mapping[str, int],
    workload: WorkloadContract,
    scenarios: Sequence[CoverageScenario],
) -> dict[str, Any]:
    """Return measured validation results for the generated clean baseline."""

    row_count_status = {
        table: {
            "expected": int(expected),
            "actual": int(len(data.get(table, ()))),
            "passed": table in data and len(data[table]) == int(expected),
        }
        for table, expected in row_counts.items()
    }
    primary_keys = _validate_primary_keys(data, schema)
    unique_constraints = _validate_unique_constraints(data, schema)
    foreign_keys = _validate_foreign_keys(data, schema)
    queries = {query.query_id: query for query in workload.queries}
    scenario_results = [
        validate_materialized_scenario(dict(data), queries[item.query_id], item)
        for item in scenarios
        if item.supported and item.row_bindings
    ]
    passed = all(item["passed"] for item in row_count_status.values())
    passed = passed and all(item["passed"] for item in primary_keys.values())
    passed = passed and all(item["passed"] for item in unique_constraints.values())
    passed = passed and all(item["passed"] for item in foreign_keys.values())
    passed = passed and all(item["passed"] for item in scenario_results)
    return {
        "passed": bool(passed),
        "row_counts": row_count_status,
        "primary_keys": primary_keys,
        "unique_constraints": unique_constraints,
        "foreign_keys": foreign_keys,
        "scenarios": scenario_results,
    }


def _validate_primary_keys(
    data: Mapping[str, pd.DataFrame], schema: DomainSchema
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for table_name, table in schema.tables.items():
        columns = tuple(table.primary_key_columns)
        if not columns or table_name not in data:
            continue
        frame = data[table_name]
        null_rows = int(frame[list(columns)].isna().any(axis=1).sum())
        duplicate_rows = int(frame.duplicated(subset=list(columns), keep=False).sum())
        result[table_name] = {
            "columns": list(columns),
            "null_rows": null_rows,
            "duplicate_rows": duplicate_rows,
            "passed": null_rows == 0 and duplicate_rows == 0,
        }
    return result


def _validate_unique_constraints(
    data: Mapping[str, pd.DataFrame], schema: DomainSchema
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for table_name, table in schema.tables.items():
        if table_name not in data:
            continue
        frame = data[table_name]
        for index, constraint in enumerate(table.unique_constraints, start=1):
            columns = list(constraint.columns)
            non_null = frame.loc[~frame[columns].isna().any(axis=1), columns]
            duplicate_rows = int(non_null.duplicated(subset=columns, keep=False).sum())
            key = constraint.name or f"{table_name}.unique_{index}"
            result[key] = {
                "table": table_name,
                "columns": columns,
                "duplicate_rows": duplicate_rows,
                "passed": duplicate_rows == 0,
            }
    return result


def _validate_foreign_keys(
    data: Mapping[str, pd.DataFrame], schema: DomainSchema
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for child_table, table in schema.tables.items():
        if child_table not in data:
            continue
        child_frame = data[child_table]
        for index, foreign_key in enumerate(table.foreign_keys, start=1):
            if foreign_key.parent_table not in data:
                continue
            child_columns = list(foreign_key.child_columns)
            parent_columns = list(foreign_key.parent_columns)
            child_keys = child_frame[child_columns]
            populated = ~child_keys.isna().any(axis=1)
            parent_keys = {
                tuple(_normalize(value) for value in row)
                for row in data[foreign_key.parent_table][parent_columns]
                .drop_duplicates()
                .itertuples(index=False, name=None)
            }
            orphan_rows = sum(
                tuple(_normalize(value) for value in row) not in parent_keys
                for row in child_keys.loc[populated].itertuples(index=False, name=None)
            )
            partial_null_rows = int(
                (child_keys.isna().any(axis=1) & ~child_keys.isna().all(axis=1)).sum()
            )
            key = foreign_key.constraint_name or f"{child_table}.foreign_key_{index}"
            result[key] = {
                "child_table": child_table,
                "child_columns": child_columns,
                "parent_table": foreign_key.parent_table,
                "parent_columns": parent_columns,
                "orphan_rows": int(orphan_rows),
                "partial_null_rows": partial_null_rows,
                "passed": int(orphan_rows) == 0 and partial_null_rows == 0,
            }
    return result


def _normalize(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    return value
