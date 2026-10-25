"""Explicit Pandas PK/FK checks; no inferred uniqueness on ordinary *_id columns."""

from __future__ import annotations


def check_keys(tables, *, primary_keys, relationships=(), non_nullable=()):
    """Validate single-column keys and (child, column, parent, column) edges.

    Nullable foreign keys use SQL-like semantics: non-null values must exist in
    the parent. Mark required columns with (table, column) in non_nullable.
    Missing tables/columns are errors, not skipped checks. This is not a general
    constraint validator and intentionally does not accept composite keys.
    """
    checks = {}

    def column(table, name):
        if not isinstance(name, str):
            raise ValueError("This helper requires single-column keys.")
        if table not in tables or name not in tables[table]:
            raise ValueError(f"Missing table/column: {table}.{name}")
        return tables[table][name]

    for table, name in primary_keys.items():
        values = column(table, name)
        checks[f"{table}.{name}:pk"] = bool(values.notna().all() and values.is_unique)
    for table, name in non_nullable:
        checks[f"{table}.{name}:not_null"] = bool(column(table, name).notna().all())
    for child, fk, parent, pk in relationships:
        parents = column(parent, pk)
        values = column(child, fk).dropna()
        checks[f"{child}.{fk}->{parent}.{pk}:fk"] = bool(values.isin(parents.dropna()).all())
        checks[f"{parent}.{pk}:referenced_unique"] = bool(parents.dropna().is_unique)
    return {
        "passed": all(checks.values()) if checks else False,
        "checks": checks,
        "warnings": [] if checks else ["No keys or relationships were checked."],
    }
