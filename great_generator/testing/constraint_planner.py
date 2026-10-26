"""Deterministic constraint planning for SQL coverage witnesses."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import replace
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from great_generator.schemas.models import ColumnSpec, DomainSchema
from great_generator.testing.coverage_model import (
    FALSE,
    TRUE,
    UNKNOWN,
    evaluate_boolean_expression,
    evaluate_predicate,
)
from great_generator.testing.query_contract import (
    CoverageScenario,
    PredicateRequirement,
    QueryContract,
    WorkloadContract,
)

SUPPORTED_COVERAGE = {
    "predicates",
    "joins",
    "boundaries",
    "null_handling",
    "negative_cases",
}
DEFAULT_COVERAGE = ("predicates", "joins", "boundaries", "null_handling")


class UnsatisfiableScenarioError(ValueError):
    """Raised when workload requirements conflict with the schema contract."""


def plan_coverage_scenarios(
    workload: WorkloadContract,
    schema: DomainSchema,
    *,
    coverage: Sequence[str] | None = None,
) -> tuple[list[CoverageScenario], list[str]]:
    """Create deterministic bounded witness scenarios for a workload."""

    requested = tuple(dict.fromkeys(coverage or DEFAULT_COVERAGE))
    unknown = sorted(set(requested) - SUPPORTED_COVERAGE)
    if unknown:
        raise ValueError(
            f"Unknown coverage targets {unknown}. Expected values from {sorted(SUPPORTED_COVERAGE)}."
        )
    scenarios: list[CoverageScenario] = []
    warnings: list[str] = []
    for query in workload.queries:
        query_scenarios, query_warnings = _plan_query(query, schema, requested)
        scenarios.extend(query_scenarios)
        warnings.extend(query_warnings)
    return scenarios, list(dict.fromkeys(warnings))


def _plan_query(
    query: QueryContract,
    schema: DomainSchema,
    requested: Sequence[str],
) -> tuple[list[CoverageScenario], list[str]]:
    if not query.supported:
        return [], [f"Query '{query.query_id}' has parser errors and was not scenario-planned."]
    scenarios: list[CoverageScenario] = []
    warnings: list[str] = []
    predicates = list(query.predicates)

    if "predicates" in requested and predicates:
        true_states = {item.requirement_id: TRUE for item in predicates}
        assignments = _solve_assignments(query, schema, true_states)
        scenarios.append(
            _scenario(
                query,
                "all_predicates_true",
                assignments,
                target_requirements=tuple(true_states),
            )
        )
        for target in predicates:
            desired = dict(true_states)
            desired[target.requirement_id] = FALSE
            try:
                assignments = _solve_assignments(query, schema, desired)
            except UnsatisfiableScenarioError as exc:
                warnings.append(
                    f"Query '{query.query_id}' cannot produce FALSE for "
                    f"'{target.expression}' without violating the schema: {exc}"
                )
                continue
            scenarios.append(
                _scenario(
                    query,
                    "individual_predicate_false",
                    assignments,
                    target_requirements=(target.requirement_id,),
                )
            )

    if "null_handling" in requested:
        for target in predicates:
            column = _column(schema, target)
            if target.operator in {"IS NULL", "IS NOT NULL"}:
                continue
            if not column.nullable:
                warnings.append(
                    f"UNKNOWN coverage for '{target.column.qualified_name}' is unavailable "
                    "because the schema declares the column NOT NULL."
                )
                continue
            desired = {item.requirement_id: TRUE for item in predicates}
            desired[target.requirement_id] = UNKNOWN
            try:
                assignments = _solve_assignments(query, schema, desired)
            except UnsatisfiableScenarioError as exc:
                warnings.append(str(exc))
                continue
            scenarios.append(
                _scenario(
                    query,
                    "predicate_unknown",
                    assignments,
                    target_requirements=(target.requirement_id,),
                )
            )

    if "boundaries" in requested:
        for target in predicates:
            for label, boundary in _boundary_values(target):
                column = _column(schema, target)
                value = _coerce_value(boundary, column)
                if not _within_contract(value, column):
                    warnings.append(
                        f"Boundary '{boundary}' for '{target.column.qualified_name}' "
                        "conflicts with the schema contract and was not generated."
                    )
                    continue
                desired = {item.requirement_id: TRUE for item in predicates}
                try:
                    assignments = _solve_assignments(query, schema, desired)
                except UnsatisfiableScenarioError as exc:
                    warnings.append(str(exc))
                    continue
                assignments[target.column.qualified_name] = value
                scenarios.append(
                    _scenario(
                        query,
                        f"boundary_{label}",
                        assignments,
                        target_requirements=(target.requirement_id,),
                    )
                )

    if "joins" in requested and query.joins:
        assignments = (
            _solve_assignments(
                query,
                schema,
                {item.requirement_id: TRUE for item in predicates},
            )
            if predicates
            else {}
        )
        scenarios.append(
            _scenario(
                query,
                "join_success",
                assignments,
                target_requirements=tuple(join.requirement_id for join in query.joins),
            )
        )

    return _deduplicate_scenarios(scenarios), warnings


def _scenario(
    query: QueryContract,
    kind: str,
    assignments: dict[str, Any],
    *,
    target_requirements: tuple[str, ...],
) -> CoverageScenario:
    states = {
        predicate.requirement_id: evaluate_predicate(
            predicate, assignments.get(predicate.column.qualified_name)
        )
        for predicate in query.predicates
    }
    outcome = evaluate_boolean_expression(query.boolean_expression, states)
    sequence = sum(1 for _ in target_requirements)
    stem = target_requirements[0] if target_requirements else f"set_{sequence}"
    return CoverageScenario(
        scenario_id=f"{query.query_id}__{kind}__{stem}",
        query_id=query.query_id,
        kind=kind,
        assignments=assignments,
        expected_predicates=states,
        expected_query_outcome=outcome,
        target_requirements=target_requirements,
    )


def _solve_assignments(
    query: QueryContract,
    schema: DomainSchema,
    desired_states: dict[str, str],
) -> dict[str, Any]:
    grouped: dict[str, list[tuple[PredicateRequirement, str]]] = defaultdict(list)
    for predicate in query.predicates:
        grouped[predicate.column.qualified_name].append(
            (predicate, desired_states.get(predicate.requirement_id, TRUE))
        )

    assignments: dict[str, Any] = {}
    for qualified_name, requirements in grouped.items():
        column = _column(schema, requirements[0][0])
        candidate = _find_candidate(requirements, column)
        if candidate is _MISSING:
            requirement_text = ", ".join(
                f"{predicate.expression}={state}" for predicate, state in requirements
            )
            allowed = list(column.accepted_values) if column.accepted_values else "not restricted"
            raise UnsatisfiableScenarioError(
                "Unable to satisfy the requested scenario:\n\n"
                f"column: {qualified_name}\n"
                f"schema_allowed_values: {allowed}\n"
                f"requirements: {requirement_text}\n\n"
                "Resolution: update the query profile or the schema contract."
            )
        assignments[qualified_name] = candidate
    return assignments


def _find_candidate(
    requirements: Sequence[tuple[PredicateRequirement, str]],
    column: ColumnSpec,
) -> Any:
    for candidate in _candidate_pool(requirements, column):
        if not _within_contract(candidate, column):
            continue
        if all(
            evaluate_predicate(predicate, candidate) == state for predicate, state in requirements
        ):
            return candidate
    return _MISSING


def _candidate_pool(
    requirements: Sequence[tuple[PredicateRequirement, str]],
    column: ColumnSpec,
) -> list[Any]:
    raw: list[Any] = []
    if any(state == UNKNOWN for _predicate, state in requirements):
        raw.append(None)
    raw.extend(column.accepted_values)
    if column.min_value is not None:
        raw.extend((column.min_value, _step(column.min_value, column, 1)))
    if column.max_value is not None:
        raw.extend((_step(column.max_value, column, -1), column.max_value))
    for predicate, _state in requirements:
        for value in predicate.values:
            raw.extend((_step(value, column, -1), value, _step(value, column, 1)))
        if len(predicate.values) == 2:
            raw.append(_midpoint(predicate.values[0], predicate.values[1], column))
    raw.extend(_generic_candidates(column))
    if column.nullable:
        raw.append(None)

    result: list[Any] = []
    seen: set[str] = set()
    for value in raw:
        try:
            normalized = _coerce_value(value, column)
        except (TypeError, ValueError, OverflowError):
            continue
        identity = repr(normalized)
        if identity not in seen:
            result.append(normalized)
            seen.add(identity)
    return result


def _boundary_values(predicate: PredicateRequirement) -> list[tuple[str, Any]]:
    if predicate.operator in {">", ">=", "<", "<="} and predicate.values:
        return [("threshold", predicate.values[0])]
    if predicate.operator in {"BETWEEN", "NOT BETWEEN"} and len(predicate.values) == 2:
        return [("lower", predicate.values[0]), ("upper", predicate.values[1])]
    return []


def _column(schema: DomainSchema, predicate: PredicateRequirement) -> ColumnSpec:
    table_name = predicate.column.table
    if table_name not in schema.tables:
        raise UnsatisfiableScenarioError(
            f"Query references table '{table_name}', which is absent from the schema contract."
        )
    for column in schema.tables[table_name].columns:
        if column.name == predicate.column.column:
            return column
    raise UnsatisfiableScenarioError(
        f"Query references unknown column '{predicate.column.qualified_name}'."
    )


def _within_contract(value: Any, column: ColumnSpec) -> bool:
    if value is None:
        return column.nullable
    if column.accepted_values:
        allowed = {_coerce_value(item, column) for item in column.accepted_values}
        if value not in allowed:
            return False
    if column.min_value is not None and value < _coerce_value(column.min_value, column):
        return False
    if column.max_value is not None and value > _coerce_value(column.max_value, column):
        return False
    return not (
        column.max_length is not None and isinstance(value, str) and len(value) > column.max_length
    )


def _coerce_value(value: Any, column: ColumnSpec) -> Any:
    if value is None:
        return None
    dtype = column.dtype.lower().strip()
    if dtype in {"int", "integer", "long", "bigint", "smallint", "short"}:
        return int(value)
    if dtype in {"float", "double", "real"}:
        return float(value)
    if dtype.startswith(("decimal", "numeric")):
        return Decimal(str(value))
    if dtype in {"bool", "boolean"}:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y"}
        return bool(value)
    if dtype == "date":
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value)[:10])
    if dtype in {"timestamp", "datetime"}:
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return str(value)


def _step(value: Any, column: ColumnSpec, direction: int) -> Any:
    if value is None:
        return None
    try:
        normalized = _coerce_value(value, column)
    except (TypeError, ValueError):
        return value
    if isinstance(normalized, datetime):
        return normalized + timedelta(seconds=direction)
    if isinstance(normalized, date):
        return normalized + timedelta(days=direction)
    if isinstance(normalized, bool):
        return not normalized
    if isinstance(normalized, Decimal):
        scale = column.scale if column.scale is not None else 2
        return normalized + Decimal(direction).scaleb(-scale)
    if isinstance(normalized, int):
        return normalized + direction
    if isinstance(normalized, float):
        return normalized + float(direction)
    if isinstance(normalized, str):
        return f"{normalized}__other" if direction > 0 else f"other__{normalized}"
    return normalized


def _midpoint(low: Any, high: Any, column: ColumnSpec) -> Any:
    left = _coerce_value(low, column)
    right = _coerce_value(high, column)
    if isinstance(left, datetime) and isinstance(right, datetime):
        return left + (right - left) / 2
    if isinstance(left, date) and isinstance(right, date):
        return left + (right - left) / 2
    if isinstance(left, (int, float, Decimal)) and isinstance(right, (int, float, Decimal)):
        return (left + right) / 2
    return left


def _generic_candidates(column: ColumnSpec) -> Iterable[Any]:
    dtype = column.dtype.lower().strip()
    if dtype in {"int", "integer", "long", "bigint", "smallint", "short"}:
        return (0, 1, -1, 10, 100)
    if dtype in {"float", "double", "real"} or dtype.startswith(("decimal", "numeric")):
        return (0, 1, -1, 0.5, 100)
    if dtype in {"bool", "boolean"}:
        return (True, False)
    if dtype == "date":
        return (date(2000, 1, 1), date(2026, 1, 1), date(2099, 12, 31))
    if dtype in {"timestamp", "datetime"}:
        return (datetime(2000, 1, 1), datetime(2026, 1, 1), datetime(2099, 12, 31))
    return ("VALUE", "OTHER", "ACTIVE", "INACTIVE")


def _deduplicate_scenarios(scenarios: Sequence[CoverageScenario]) -> list[CoverageScenario]:
    counts: dict[str, int] = defaultdict(int)
    result: list[CoverageScenario] = []
    for scenario in scenarios:
        counts[scenario.scenario_id] += 1
        if counts[scenario.scenario_id] == 1:
            result.append(scenario)
        else:
            result.append(
                replace(
                    scenario,
                    scenario_id=f"{scenario.scenario_id}_{counts[scenario.scenario_id]}",
                )
            )
    return result


_MISSING = object()
