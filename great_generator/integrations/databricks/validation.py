"""Relational validation for Unity Catalog-derived synthetic datasets."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from .models import UCRelationshipMetadata, UCTableMetadata


def validate_uc_relational_data(
    data: Mapping[str, Any],
    tables: Mapping[str, UCTableMetadata],
    relationships: Sequence[UCRelationshipMetadata],
    *,
    expected_anomalies: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Validate row counts, primary keys, and foreign keys for Pandas or Spark outputs."""

    if not data:
        return {
            "passed": True,
            "engine": "unknown",
            "row_counts": {},
            "primary_keys": {},
            "unique_constraints": {},
            "foreign_keys": {},
            "expected_anomalies": dict(expected_anomalies or {}),
            "unexpected_violations": [],
        }
    first = next(iter(data.values()))
    if isinstance(first, pd.DataFrame):
        return _validate_pandas(data, tables, relationships, expected_anomalies)
    return _validate_spark(data, tables, relationships, expected_anomalies)


def _validate_pandas(
    data: Mapping[str, pd.DataFrame],
    tables: Mapping[str, UCTableMetadata],
    relationships: Sequence[UCRelationshipMetadata],
    expected_anomalies: Mapping[str, float] | None,
) -> dict[str, Any]:
    aliases = _table_aliases(tables)
    primary: dict[str, Any] = {}
    unique: dict[str, Any] = {}
    foreign: dict[str, Any] = {}
    unexpected: list[str] = []
    for qualified, metadata in tables.items():
        alias = aliases[qualified]
        if alias not in data:
            continue
        keys = metadata.primary_key_columns
        if not keys:
            primary[alias] = {"checked": False, "reason": "no declared primary key"}
            continue
        frame = data[alias]
        null_rows = int(frame[list(keys)].isna().any(axis=1).sum())
        duplicate_rows = int(frame.duplicated(subset=list(keys), keep=False).sum())
        primary[alias] = {
            "checked": True,
            "columns": list(keys),
            "null_rows": null_rows,
            "duplicate_rows": duplicate_rows,
            "passed": null_rows == 0 and duplicate_rows == 0,
        }
        if null_rows or (duplicate_rows and not _expects_duplicates(expected_anomalies)):
            unexpected.append(f"{alias}: primary-key violations")
        for constraint in metadata.constraints:
            if constraint.constraint_type != "UNIQUE" or not constraint.columns:
                continue
            unique_frame = frame.loc[
                frame[list(constraint.columns)].notna().all(axis=1),
                list(constraint.columns),
            ]
            duplicate_count = int(unique_frame.duplicated(keep=False).sum())
            unique[constraint.name] = {
                "table": alias,
                "columns": list(constraint.columns),
                "duplicate_rows": duplicate_count,
                "passed": duplicate_count == 0,
            }
            if duplicate_count and not _expects_duplicates(expected_anomalies):
                unexpected.append(f"{alias}: unique constraint '{constraint.name}' violations")

    for relationship in relationships:
        child_alias = aliases.get(relationship.child_table)
        parent_alias = aliases.get(relationship.parent_table)
        key = _relationship_key(relationship)
        if child_alias not in data or parent_alias not in data:
            foreign[key] = {"checked": False, "reason": "table not generated"}
            continue
        child = data[child_alias]
        parent = data[parent_alias]
        child_columns = list(relationship.child_columns)
        parent_columns = list(relationship.parent_columns)
        non_null = child[child_columns].notna().all(axis=1)
        partial_null_rows = int(
            (
                child[child_columns].notna().any(axis=1) & ~child[child_columns].notna().all(axis=1)
            ).sum()
        )
        child_keys = child.loc[non_null, child_columns].copy()
        child_keys.columns = parent_columns
        parent_keys = parent[parent_columns].drop_duplicates()
        merged = child_keys.merge(parent_keys, on=parent_columns, how="left", indicator=True)
        orphan_rows = int((merged["_merge"] == "left_only").sum())
        foreign[key] = {
            "checked": True,
            "child_columns": child_columns,
            "parent_columns": parent_columns,
            "orphan_rows": orphan_rows,
            "partial_null_rows": partial_null_rows,
            "passed": orphan_rows == 0 and partial_null_rows == 0,
        }
        if orphan_rows and not _expects_orphans(expected_anomalies):
            unexpected.append(f"{key}: {orphan_rows} orphan row(s)")
        if partial_null_rows:
            unexpected.append(f"{key}: {partial_null_rows} partial composite-null row(s)")

    constraints_passed = all(
        not item.get("checked") or item.get("passed", True)
        for item in [*primary.values(), *unique.values(), *foreign.values()]
    )
    return {
        "passed": not unexpected,
        "constraints_passed": constraints_passed,
        "engine": "pandas",
        "row_counts": {name: int(len(frame)) for name, frame in data.items()},
        "primary_keys": primary,
        "unique_constraints": unique,
        "foreign_keys": foreign,
        "expected_anomalies": dict(expected_anomalies or {}),
        "unexpected_violations": unexpected,
    }


def _validate_spark(
    data: Mapping[str, Any],
    tables: Mapping[str, UCTableMetadata],
    relationships: Sequence[UCRelationshipMetadata],
    expected_anomalies: Mapping[str, float] | None,
) -> dict[str, Any]:
    try:
        from pyspark.sql import functions as F
    except ImportError as exc:
        raise ImportError("Spark validation requires: pip install great-generator[spark]") from exc
    aliases = _table_aliases(tables)
    primary: dict[str, Any] = {}
    unique: dict[str, Any] = {}
    foreign: dict[str, Any] = {}
    unexpected: list[str] = []
    row_counts = {name: int(frame.count()) for name, frame in data.items()}
    for qualified, metadata in tables.items():
        alias = aliases[qualified]
        if alias not in data:
            continue
        keys = metadata.primary_key_columns
        if not keys:
            primary[alias] = {"checked": False, "reason": "no declared primary key"}
            continue
        frame = data[alias]
        null_predicate = None
        for column in keys:
            expression = F.col(column).isNull()
            null_predicate = expression if null_predicate is None else null_predicate | expression
        null_rows = int(frame.filter(null_predicate).count())
        duplicate_rows = int(
            frame.groupBy(*keys).count().filter(F.col("count") > 1).agg(F.sum("count")).first()[0]
            or 0
        )
        primary[alias] = {
            "checked": True,
            "columns": list(keys),
            "null_rows": null_rows,
            "duplicate_rows": duplicate_rows,
            "passed": null_rows == 0 and duplicate_rows == 0,
        }
        if null_rows or (duplicate_rows and not _expects_duplicates(expected_anomalies)):
            unexpected.append(f"{alias}: primary-key violations")
        for constraint in metadata.constraints:
            if constraint.constraint_type != "UNIQUE" or not constraint.columns:
                continue
            unique_non_null = None
            for column in constraint.columns:
                expression = F.col(column).isNotNull()
                unique_non_null = (
                    expression if unique_non_null is None else unique_non_null & expression
                )
            duplicate_count = int(
                frame.filter(unique_non_null)
                .groupBy(*constraint.columns)
                .count()
                .filter(F.col("count") > 1)
                .agg(F.sum("count"))
                .first()[0]
                or 0
            )
            unique[constraint.name] = {
                "table": alias,
                "columns": list(constraint.columns),
                "duplicate_rows": duplicate_count,
                "passed": duplicate_count == 0,
            }
            if duplicate_count and not _expects_duplicates(expected_anomalies):
                unexpected.append(f"{alias}: unique constraint '{constraint.name}' violations")

    for relationship in relationships:
        child_alias = aliases.get(relationship.child_table)
        parent_alias = aliases.get(relationship.parent_table)
        key = _relationship_key(relationship)
        if child_alias not in data or parent_alias not in data:
            foreign[key] = {"checked": False, "reason": "table not generated"}
            continue
        child = data[child_alias]
        parent = data[parent_alias]
        child_aliased = child.alias("child")
        parent_aliased = parent.alias("parent")
        condition = None
        for child_column, parent_column in zip(
            relationship.child_columns, relationship.parent_columns
        ):
            expression = F.col(f"child.`{child_column}`") == F.col(f"parent.`{parent_column}`")
            condition = expression if condition is None else condition & expression
        non_null = None
        any_non_null = None
        for column in relationship.child_columns:
            expression = F.col(f"child.`{column}`").isNotNull()
            non_null = expression if non_null is None else non_null & expression
            any_non_null = expression if any_non_null is None else any_non_null | expression
        partial_null_rows = int(child_aliased.filter(any_non_null & ~non_null).count())
        orphan_rows = int(
            child_aliased.filter(non_null).join(parent_aliased, condition, "left_anti").count()
        )
        foreign[key] = {
            "checked": True,
            "child_columns": list(relationship.child_columns),
            "parent_columns": list(relationship.parent_columns),
            "orphan_rows": orphan_rows,
            "partial_null_rows": partial_null_rows,
            "passed": orphan_rows == 0 and partial_null_rows == 0,
        }
        if orphan_rows and not _expects_orphans(expected_anomalies):
            unexpected.append(f"{key}: {orphan_rows} orphan row(s)")
        if partial_null_rows:
            unexpected.append(f"{key}: {partial_null_rows} partial composite-null row(s)")
    constraints_passed = all(
        not item.get("checked") or item.get("passed", True)
        for item in [*primary.values(), *unique.values(), *foreign.values()]
    )
    return {
        "passed": not unexpected,
        "constraints_passed": constraints_passed,
        "engine": "spark",
        "row_counts": row_counts,
        "primary_keys": primary,
        "unique_constraints": unique,
        "foreign_keys": foreign,
        "expected_anomalies": dict(expected_anomalies or {}),
        "unexpected_violations": unexpected,
    }


def _table_aliases(tables: Mapping[str, UCTableMetadata]) -> dict[str, str]:
    return {qualified: metadata.name.table for qualified, metadata in tables.items()}


def _relationship_key(relationship: UCRelationshipMetadata) -> str:
    child = ",".join(relationship.child_columns)
    parent = ",".join(relationship.parent_columns)
    return f"{relationship.child_table}[{child}] -> {relationship.parent_table}[{parent}]"


def _expects_orphans(anomalies: Mapping[str, float] | None) -> bool:
    return bool((anomalies or {}).get("orphan_fk_rate", 0))


def _expects_duplicates(anomalies: Mapping[str, float] | None) -> bool:
    return bool((anomalies or {}).get("duplicate_rate", 0))
