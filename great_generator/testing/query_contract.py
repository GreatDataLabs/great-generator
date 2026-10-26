"""Validated workload contracts for contract-to-test generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class QueryDiagnostic:
    """A parser or planner diagnostic tied to a query workload."""

    code: str
    message: str
    severity: str = "warning"
    fragment: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ColumnReference:
    """A resolved table-qualified column reference."""

    table: str
    column: str

    @property
    def qualified_name(self) -> str:
        return f"{self.table}.{self.column}"

    def to_dict(self) -> dict[str, str]:
        return {"table": self.table, "column": self.column, "qualified_name": self.qualified_name}


@dataclass(frozen=True)
class PredicateRequirement:
    """One supported atomic SQL predicate."""

    requirement_id: str
    column: ColumnReference
    operator: str
    values: tuple[Any, ...]
    expression: str
    negated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "column": self.column.to_dict(),
            "operator": self.operator,
            "values": list(self.values),
            "expression": self.expression,
            "negated": self.negated,
        }


@dataclass(frozen=True)
class JoinRequirement:
    """One equality join path extracted from SQL."""

    requirement_id: str
    left: ColumnReference
    right: ColumnReference
    join_type: str
    expression: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "join_type": self.join_type,
            "expression": self.expression,
        }


@dataclass(frozen=True)
class AggregateRequirement:
    """An aggregate expression and its optional source column."""

    function: str
    expression: str
    column: ColumnReference | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"function": self.function, "expression": self.expression}
        payload["column"] = self.column.to_dict() if self.column else None
        return payload


@dataclass(frozen=True)
class BooleanExpression:
    """Serializable SQL boolean tree over predicate requirement IDs."""

    kind: str
    predicate_id: str | None = None
    children: tuple[BooleanExpression, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "predicate_id": self.predicate_id,
            "children": [child.to_dict() for child in self.children],
        }


@dataclass(frozen=True)
class QueryContract:
    """Normalized, inspectable requirements for one SQL SELECT query."""

    query_id: str
    sql: str
    dialect: str | None
    tables: tuple[str, ...]
    columns: tuple[ColumnReference, ...]
    joins: tuple[JoinRequirement, ...]
    predicates: tuple[PredicateRequirement, ...]
    boolean_expression: BooleanExpression | None
    group_by: tuple[ColumnReference, ...]
    aggregates: tuple[AggregateRequirement, ...]
    diagnostics: tuple[QueryDiagnostic, ...] = ()

    @property
    def supported(self) -> bool:
        return not any(item.severity == "error" for item in self.diagnostics)

    @property
    def is_conjunctive(self) -> bool:
        def supported_tree(node: BooleanExpression | None) -> bool:
            if node is None or node.kind == "predicate":
                return True
            return node.kind == "and" and all(supported_tree(child) for child in node.children)

        return supported_tree(self.boolean_expression)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "sql": self.sql,
            "dialect": self.dialect,
            "tables": list(self.tables),
            "columns": [column.to_dict() for column in self.columns],
            "joins": [join.to_dict() for join in self.joins],
            "predicates": [predicate.to_dict() for predicate in self.predicates],
            "boolean_expression": (
                self.boolean_expression.to_dict() if self.boolean_expression else None
            ),
            "group_by": [column.to_dict() for column in self.group_by],
            "aggregates": [aggregate.to_dict() for aggregate in self.aggregates],
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
            "supported": self.supported,
            "is_conjunctive": self.is_conjunctive,
        }


@dataclass(frozen=True)
class WorkloadContract:
    """Normalized contract for a deterministic collection of SQL queries."""

    queries: tuple[QueryContract, ...]
    source_files: tuple[str, ...] = ()
    diagnostics: tuple[QueryDiagnostic, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "queries": [query.to_dict() for query in self.queries],
            "source_files": list(self.source_files),
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
        }


@dataclass(frozen=True)
class CoverageScenario:
    """One bounded witness scenario generated from query requirements."""

    scenario_id: str
    query_id: str
    kind: str
    assignments: dict[str, Any]
    expected_predicates: dict[str, str]
    expected_query_outcome: str
    target_requirements: tuple[str, ...]
    row_bindings: dict[str, int] = field(default_factory=dict)
    supported: bool = True
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "query_id": self.query_id,
            "kind": self.kind,
            "assignments": _jsonable(self.assignments),
            "expected_predicates": dict(self.expected_predicates),
            "expected_query_outcome": self.expected_query_outcome,
            "target_requirements": list(self.target_requirements),
            "row_bindings": dict(self.row_bindings),
            "supported": self.supported,
            "warnings": list(self.warnings),
        }


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    return value
