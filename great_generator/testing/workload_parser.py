"""SQL workload parsing for the documented contract-to-test subset."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Any

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from great_generator.schemas.models import ContractSchema, DomainSchema
from great_generator.testing.query_contract import (
    AggregateRequirement,
    BooleanExpression,
    ColumnReference,
    JoinRequirement,
    PredicateRequirement,
    QueryContract,
    QueryDiagnostic,
    WorkloadContract,
)

_COMPARISONS: dict[type[exp.Expression], str] = {
    exp.EQ: "=",
    exp.NEQ: "!=",
    exp.GT: ">",
    exp.GTE: ">=",
    exp.LT: "<",
    exp.LTE: "<=",
}
_INVERTED_COMPARISONS = {"=": "=", "!=": "!=", ">": "<", ">=": "<=", "<": ">", "<=": ">="}


def parse_sql_workload(
    queries: str | Path | Sequence[str | Path],
    *,
    schema: DomainSchema | ContractSchema | Mapping[str, Sequence[str]] | None = None,
    dialect: str | None = None,
) -> WorkloadContract:
    """Parse SQL strings or files into an inspectable workload contract.

    Parsing never executes SQL. The current compiler validates ``SELECT`` workloads and
    records explicit diagnostics for syntax that is parsed but not yet scenario-planned.
    """

    items = _query_items(queries)
    query_contracts: list[QueryContract] = []
    source_files: list[str] = []
    schema_columns = _schema_columns(schema)
    for index, item in enumerate(items, start=1):
        sql, query_id, source_file = _read_query(item, index)
        if source_file:
            source_files.append(source_file)
        query_contracts.append(
            _parse_query(
                sql,
                query_id=query_id,
                dialect=dialect,
                schema_columns=schema_columns,
            )
        )
    return WorkloadContract(queries=tuple(query_contracts), source_files=tuple(source_files))


def _query_items(queries: str | Path | Sequence[str | Path]) -> list[str | Path]:
    if isinstance(queries, (str, Path)):
        return [queries]
    items = list(queries)
    if not items:
        raise ValueError("queries must include at least one SQL string or file path.")
    return items


def _read_query(item: str | Path, index: int) -> tuple[str, str, str | None]:
    path = Path(item)
    try:
        is_file = path.is_file()
    except OSError:
        is_file = False
    if is_file:
        sql = path.read_text(encoding="utf-8").strip()
        if not sql:
            raise ValueError(f"SQL workload file '{path}' is empty.")
        return sql, path.stem, str(path)
    sql = str(item).strip()
    if not sql:
        raise ValueError("SQL workload entries cannot be empty.")
    return sql, f"query_{index:03d}", None


def _parse_query(
    sql: str,
    *,
    query_id: str,
    dialect: str | None,
    schema_columns: Mapping[str, set[str]],
) -> QueryContract:
    diagnostics: list[QueryDiagnostic] = []
    try:
        statements = sqlglot.parse(sql, read=dialect)
    except (ParseError, ValueError) as exc:
        return _failed_query(query_id, sql, dialect, "sql_parse_error", str(exc))
    if len(statements) != 1:
        return _failed_query(
            query_id,
            sql,
            dialect,
            "multiple_statements",
            "Each workload entry must contain exactly one SQL statement.",
        )
    root = statements[0]
    select = root if isinstance(root, exp.Select) else root.find(exp.Select)
    if select is None or not isinstance(root, exp.Select):
        return _failed_query(
            query_id,
            sql,
            dialect,
            "unsupported_statement",
            "The Phase 1 workload compiler accepts a single top-level SELECT statement.",
        )

    _append_structure_diagnostics(root, diagnostics)
    tables, aliases = _tables_and_aliases(select)
    columns = _columns(select, aliases, tables, schema_columns, diagnostics)
    joins = _joins(select, aliases, tables, schema_columns, diagnostics)
    predicates: list[PredicateRequirement] = []
    boolean_expression: BooleanExpression | None = None
    where = select.args.get("where")
    if where is not None:
        boolean_expression = _boolean_expression(
            where.this,
            predicates,
            aliases,
            tables,
            schema_columns,
            diagnostics,
        )
    if boolean_expression is not None and not _is_conjunctive(boolean_expression):
        diagnostics.append(
            QueryDiagnostic(
                code="boolean_planning_partial",
                message=(
                    "OR and NOT are represented in the workload contract, but Phase 1 "
                    "scenario allocation guarantees combined outcomes only for conjunctive WHERE clauses."
                ),
            )
        )

    group_by = _group_by(select, aliases, tables, schema_columns, diagnostics)
    aggregates = _aggregates(select, aliases, tables, schema_columns, diagnostics)
    return QueryContract(
        query_id=query_id,
        sql=sql,
        dialect=dialect,
        tables=tuple(tables),
        columns=tuple(columns),
        joins=tuple(joins),
        predicates=tuple(predicates),
        boolean_expression=boolean_expression,
        group_by=tuple(group_by),
        aggregates=tuple(aggregates),
        diagnostics=tuple(_deduplicate_diagnostics(diagnostics)),
    )


def _failed_query(
    query_id: str,
    sql: str,
    dialect: str | None,
    code: str,
    message: str,
) -> QueryContract:
    return QueryContract(
        query_id=query_id,
        sql=sql,
        dialect=dialect,
        tables=(),
        columns=(),
        joins=(),
        predicates=(),
        boolean_expression=None,
        group_by=(),
        aggregates=(),
        diagnostics=(QueryDiagnostic(code=code, message=message, severity="error"),),
    )


def _append_structure_diagnostics(root: exp.Expression, diagnostics: list[QueryDiagnostic]) -> None:
    checks = (
        (exp.CTE, "cte_not_planned", "CTEs are parsed but not scenario-planned in Phase 1."),
        (exp.Subquery, "subquery_not_planned", "Subqueries are not scenario-planned in Phase 1."),
        (exp.Window, "window_not_planned", "Window functions are not scenario-planned in Phase 1."),
        (
            exp.Having,
            "having_not_planned",
            "HAVING predicates are not scenario-planned in Phase 1.",
        ),
    )
    for expression_type, code, message in checks:
        if root.find(expression_type) is not None:
            diagnostics.append(QueryDiagnostic(code=code, message=message))


def _tables_and_aliases(select: exp.Select) -> tuple[list[str], dict[str, str]]:
    tables: list[str] = []
    aliases: dict[str, str] = {}
    for table in select.find_all(exp.Table):
        name = table.name
        if name not in tables:
            tables.append(name)
        aliases[name] = name
        if table.alias:
            aliases[table.alias] = name
    return tables, aliases


def _columns(
    select: exp.Select,
    aliases: Mapping[str, str],
    tables: Sequence[str],
    schema_columns: Mapping[str, set[str]],
    diagnostics: list[QueryDiagnostic],
) -> list[ColumnReference]:
    seen: set[str] = set()
    result: list[ColumnReference] = []
    for column in select.find_all(exp.Column):
        resolved = _resolve_column(column, aliases, tables, schema_columns, diagnostics)
        if resolved is not None and resolved.qualified_name not in seen:
            result.append(resolved)
            seen.add(resolved.qualified_name)
    return result


def _joins(
    select: exp.Select,
    aliases: Mapping[str, str],
    tables: Sequence[str],
    schema_columns: Mapping[str, set[str]],
    diagnostics: list[QueryDiagnostic],
) -> list[JoinRequirement]:
    result: list[JoinRequirement] = []
    for join in select.args.get("joins") or ():
        side = str(join.args.get("side") or "INNER").upper()
        kind = str(join.args.get("kind") or "").upper()
        join_type = " ".join(item for item in (side, kind, "JOIN") if item).replace(
            "INNER JOIN", "INNER JOIN"
        )
        if side not in {"", "INNER", "LEFT"} or kind not in {"", "INNER"}:
            diagnostics.append(
                QueryDiagnostic(
                    code="unsupported_join_type",
                    message=f"Join type '{join_type.strip()}' is parsed but not scenario-planned.",
                    fragment=join.sql(),
                )
            )
        on = join.args.get("on")
        if on is None:
            diagnostics.append(
                QueryDiagnostic(
                    code="join_without_on",
                    message="JOIN clauses require an ON equality condition in Phase 1.",
                    fragment=join.sql(),
                )
            )
            continue
        for expression in _flatten_and(on):
            if (
                not isinstance(expression, exp.EQ)
                or not isinstance(expression.this, exp.Column)
                or not isinstance(expression.expression, exp.Column)
            ):
                diagnostics.append(
                    QueryDiagnostic(
                        code="unsupported_join_condition",
                        message="Only column-to-column equality joins are scenario-planned.",
                        fragment=expression.sql(),
                    )
                )
                continue
            left = _resolve_column(expression.this, aliases, tables, schema_columns, diagnostics)
            right = _resolve_column(
                expression.expression, aliases, tables, schema_columns, diagnostics
            )
            if left is None or right is None:
                continue
            result.append(
                JoinRequirement(
                    requirement_id=f"join_{len(result) + 1:03d}",
                    left=left,
                    right=right,
                    join_type="LEFT" if side == "LEFT" else "INNER",
                    expression=expression.sql(),
                )
            )
    return result


def _boolean_expression(
    expression: exp.Expression,
    predicates: list[PredicateRequirement],
    aliases: Mapping[str, str],
    tables: Sequence[str],
    schema_columns: Mapping[str, set[str]],
    diagnostics: list[QueryDiagnostic],
) -> BooleanExpression:
    if isinstance(expression, exp.Paren):
        return _boolean_expression(
            expression.this, predicates, aliases, tables, schema_columns, diagnostics
        )
    if isinstance(expression, (exp.And, exp.Or)):
        return BooleanExpression(
            kind="and" if isinstance(expression, exp.And) else "or",
            children=(
                _boolean_expression(
                    expression.this, predicates, aliases, tables, schema_columns, diagnostics
                ),
                _boolean_expression(
                    expression.expression,
                    predicates,
                    aliases,
                    tables,
                    schema_columns,
                    diagnostics,
                ),
            ),
        )
    if isinstance(expression, exp.Not) and not isinstance(
        expression.this, (exp.In, exp.Is, exp.Between)
    ):
        return BooleanExpression(
            kind="not",
            children=(
                _boolean_expression(
                    expression.this, predicates, aliases, tables, schema_columns, diagnostics
                ),
            ),
        )
    predicate = _atomic_predicate(
        expression, predicates, aliases, tables, schema_columns, diagnostics
    )
    if predicate is None:
        return BooleanExpression(kind="unsupported")
    predicates.append(predicate)
    return BooleanExpression(kind="predicate", predicate_id=predicate.requirement_id)


def _atomic_predicate(
    expression: exp.Expression,
    predicates: Sequence[PredicateRequirement],
    aliases: Mapping[str, str],
    tables: Sequence[str],
    schema_columns: Mapping[str, set[str]],
    diagnostics: list[QueryDiagnostic],
) -> PredicateRequirement | None:
    negated = False
    raw = expression
    if isinstance(raw, exp.Not):
        negated = True
        raw = raw.this

    operator: str | None = None
    column_expression: exp.Column | None = None
    values: tuple[Any, ...] = ()
    for expression_type, symbol in _COMPARISONS.items():
        if isinstance(raw, expression_type):
            left, right = raw.this, raw.expression
            if isinstance(left, exp.Column) and _is_literal(right):
                column_expression = left
                operator = symbol
                values = (_literal_value(right),)
            elif isinstance(right, exp.Column) and _is_literal(left):
                column_expression = right
                operator = _INVERTED_COMPARISONS[symbol]
                values = (_literal_value(left),)
            break
    if isinstance(raw, exp.In) and isinstance(raw.this, exp.Column):
        if raw.args.get("query") is not None or not all(
            _is_literal(item) for item in raw.expressions
        ):
            return _unsupported_predicate(raw, diagnostics, "IN subqueries are not supported.")
        column_expression = raw.this
        operator = "NOT IN" if negated else "IN"
        values = tuple(_literal_value(item) for item in raw.expressions)
        negated = False
    elif isinstance(raw, exp.Between) and isinstance(raw.this, exp.Column):
        low, high = raw.args.get("low"), raw.args.get("high")
        if not _is_literal(low) or not _is_literal(high):
            return _unsupported_predicate(raw, diagnostics, "BETWEEN bounds must be literals.")
        column_expression = raw.this
        operator = "NOT BETWEEN" if negated else "BETWEEN"
        values = (_literal_value(low), _literal_value(high))
        negated = False
    elif isinstance(raw, exp.Is) and isinstance(raw.this, exp.Column):
        if not isinstance(raw.expression, exp.Null):
            return _unsupported_predicate(raw, diagnostics, "Only IS NULL is supported.")
        column_expression = raw.this
        operator = "IS NOT NULL" if negated else "IS NULL"
        negated = False

    if column_expression is None or operator is None:
        return _unsupported_predicate(
            expression,
            diagnostics,
            "Predicate is outside the documented comparison, IN, BETWEEN, and NULL subset.",
        )
    column = _resolve_column(column_expression, aliases, tables, schema_columns, diagnostics)
    if column is None:
        return None
    if negated:
        operator = f"NOT ({operator})"
    return PredicateRequirement(
        requirement_id=f"predicate_{len(predicates) + 1:03d}",
        column=column,
        operator=operator,
        values=values,
        expression=expression.sql(),
        negated=negated,
    )


def _unsupported_predicate(
    expression: exp.Expression,
    diagnostics: list[QueryDiagnostic],
    message: str,
) -> None:
    diagnostics.append(
        QueryDiagnostic(
            code="unsupported_predicate",
            message=message,
            fragment=expression.sql(),
        )
    )
    return None


def _group_by(
    select: exp.Select,
    aliases: Mapping[str, str],
    tables: Sequence[str],
    schema_columns: Mapping[str, set[str]],
    diagnostics: list[QueryDiagnostic],
) -> list[ColumnReference]:
    group = select.args.get("group")
    if group is None:
        return []
    result: list[ColumnReference] = []
    for expression in group.expressions:
        if not isinstance(expression, exp.Column):
            diagnostics.append(
                QueryDiagnostic(
                    code="unsupported_group_expression",
                    message="Phase 1 records GROUP BY columns but not computed group expressions.",
                    fragment=expression.sql(),
                )
            )
            continue
        column = _resolve_column(expression, aliases, tables, schema_columns, diagnostics)
        if column is not None:
            result.append(column)
    return result


def _aggregates(
    select: exp.Select,
    aliases: Mapping[str, str],
    tables: Sequence[str],
    schema_columns: Mapping[str, set[str]],
    diagnostics: list[QueryDiagnostic],
) -> list[AggregateRequirement]:
    result: list[AggregateRequirement] = []
    for aggregate in select.find_all(exp.AggFunc):
        source = next(aggregate.find_all(exp.Column), None)
        column = (
            _resolve_column(source, aliases, tables, schema_columns, diagnostics)
            if source is not None
            else None
        )
        result.append(
            AggregateRequirement(
                function=aggregate.key.upper(), expression=aggregate.sql(), column=column
            )
        )
    return result


def _resolve_column(
    column: exp.Column,
    aliases: Mapping[str, str],
    tables: Sequence[str],
    schema_columns: Mapping[str, set[str]],
    diagnostics: list[QueryDiagnostic],
) -> ColumnReference | None:
    column_name = column.name
    qualifier = column.table
    if qualifier:
        table_name = aliases.get(qualifier, qualifier)
        if schema_columns and table_name not in schema_columns:
            diagnostics.append(
                QueryDiagnostic(
                    code="unknown_table",
                    severity="error",
                    message=f"Column '{column.sql()}' references unknown table '{table_name}'.",
                    fragment=column.sql(),
                )
            )
            return None
        if schema_columns and column_name not in schema_columns.get(table_name, set()):
            diagnostics.append(
                QueryDiagnostic(
                    code="unknown_column",
                    severity="error",
                    message=f"Column '{column.sql()}' is not present in table '{table_name}'.",
                    fragment=column.sql(),
                )
            )
            return None
        return ColumnReference(table=table_name, column=column_name)

    candidates = [
        table_name
        for table_name in tables
        if not schema_columns or column_name in schema_columns.get(table_name, set())
    ]
    if len(candidates) == 1:
        return ColumnReference(table=candidates[0], column=column_name)
    if not candidates and len(tables) == 1 and not schema_columns:
        return ColumnReference(table=tables[0], column=column_name)
    diagnostics.append(
        QueryDiagnostic(
            code="ambiguous_column" if candidates else "unknown_column",
            severity="error",
            message=(
                f"Unqualified column '{column_name}' matches multiple workload tables: {candidates}."
                if candidates
                else f"Unqualified column '{column_name}' could not be resolved."
            ),
            fragment=column.sql(),
        )
    )
    return None


def _flatten_and(expression: exp.Expression) -> list[exp.Expression]:
    if isinstance(expression, exp.And):
        return [*_flatten_and(expression.this), *_flatten_and(expression.expression)]
    return [expression]


def _is_literal(expression: Any) -> bool:
    if isinstance(expression, (exp.Literal, exp.Boolean, exp.Null)):
        return True
    return isinstance(expression, exp.Cast) and _is_literal(expression.this)


def _literal_value(expression: exp.Expression) -> Any:
    if isinstance(expression, exp.Cast):
        raw = _literal_value(expression.this)
        target = str(expression.args.get("to") or "").upper()
        if "TIMESTAMP" in target:
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if "DATE" in target:
            return date.fromisoformat(str(raw))
        return raw
    if isinstance(expression, exp.Null):
        return None
    if isinstance(expression, exp.Boolean):
        return str(expression.this).strip().upper() == "TRUE"
    if isinstance(expression, exp.Literal):
        if expression.is_string:
            return str(expression.this)
        text = str(expression.this)
        try:
            return int(text)
        except ValueError:
            try:
                return float(text)
            except ValueError:
                return text
    raise TypeError(f"Unsupported SQL literal '{expression.sql()}'.")


def _schema_columns(
    schema: DomainSchema | ContractSchema | Mapping[str, Sequence[str]] | None,
) -> dict[str, set[str]]:
    if schema is None:
        return {}
    if isinstance(schema, (DomainSchema, ContractSchema)):
        return {
            table_name: set(table.column_names()) for table_name, table in schema.tables.items()
        }
    return {str(table): {str(column) for column in columns} for table, columns in schema.items()}


def _is_conjunctive(node: BooleanExpression | None) -> bool:
    if node is None or node.kind == "predicate":
        return True
    return node.kind == "and" and all(_is_conjunctive(child) for child in node.children)


def _deduplicate_diagnostics(items: Sequence[QueryDiagnostic]) -> list[QueryDiagnostic]:
    seen: set[tuple[str, str, str | None]] = set()
    result: list[QueryDiagnostic] = []
    for item in items:
        identity = (item.code, item.message, item.fragment)
        if identity not in seen:
            result.append(item)
            seen.add(identity)
    return result
