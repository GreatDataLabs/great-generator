"""Deterministic contract diff and conservative fixture impact, not a migration engine."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from great_generator import parse_ddl

TYPE_FIELDS = {"dtype", "original_type", "logical_type", "precision", "scale", "max_length"}
CONSTRAINT_FIELDS = {"min_value", "max_value", "accepted_values"}


def compare_contracts(old, new):
    """Compare ContractSchema instances, including transitive dependents from BOTH graphs.

    Impact labels are review priorities, not guarantees of backwards compatibility.
    Renames are deliberately reported as removals/additions. Changed SQL CHECK text
    is not evaluated. Fingerprints include metadata, not just physical schema.
    """
    before, after = old.canonical_dict(), new.canonical_dict()
    changes = []

    def add(kind, table, column=None, prior=None, current=None, impact="review"):
        changes.append(
            {
                "kind": kind,
                "table": table,
                "column": column,
                "before": prior,
                "after": current,
                "impact": impact,
            }
        )

    for name in sorted(set(before["tables"]) | set(after["tables"])):
        left, right = before["tables"].get(name), after["tables"].get(name)
        if left is None or right is None:
            add(
                "TABLE_ADDED" if left is None else "TABLE_REMOVED",
                name,
                prior=left,
                current=right,
                impact="high" if right is None else "review",
            )
            continue
        old_columns = {c["name"]: c for c in left["columns"]}
        new_columns = {c["name"]: c for c in right["columns"]}
        for column in sorted(set(old_columns) | set(new_columns)):
            a, b = old_columns.get(column), new_columns.get(column)
            if a is None or b is None:
                add(
                    "COLUMN_ADDED" if a is None else "COLUMN_REMOVED",
                    name,
                    column,
                    a,
                    b,
                    "high" if b is None or not b["nullable"] else "low",
                )
                continue
            for field in sorted(set(a) | set(b)):
                if a.get(field) == b.get(field):
                    continue
                if field in TYPE_FIELDS:
                    kind, impact = "TYPE_CHANGED", "review"
                elif field == "nullable":
                    kind, impact = "NULLABILITY_CHANGED", "high" if not b[field] else "low"
                elif field == "default_expression":
                    kind, impact = "DEFAULT_CHANGED", "review"
                elif field in CONSTRAINT_FIELDS:
                    kind, impact = "CONSTRAINT_CHANGED", "review"
                else:
                    kind, impact = "METADATA_CHANGED", "review"
                if field in TYPE_FIELDS and (
                    column in left["primary_key_columns"] or column in right["primary_key_columns"]
                ):
                    impact = "high"
                add(kind, name, column, {field: a.get(field)}, {field: b.get(field)}, impact)
        if list(old_columns) != list(new_columns):
            add("COLUMN_ORDER_CHANGED", name, prior=list(old_columns), current=list(new_columns))
        kinds = {
            "primary_key_columns": "PK_CHANGED",
            "foreign_keys": "FK_CHANGED",
            "unique_constraints": "CONSTRAINT_CHANGED",
            "checks": "CONSTRAINT_CHANGED",
        }
        for field in sorted((set(left) | set(right)) - {"columns"}):
            if left.get(field) != right.get(field):
                kind = kinds.get(field, "METADATA_CHANGED")
                add(
                    kind,
                    name,
                    prior={field: left.get(field)},
                    current={field: right.get(field)},
                    impact="high" if kind in {"PK_CHANGED", "FK_CHANGED"} else "review",
                )

    changed = {item["table"] for item in changes}
    contract_metadata = {
        key: {"before": before.get(key), "after": after.get(key)}
        for key in sorted((set(before) | set(after)) - {"tables"})
        if before.get(key) != after.get(key)
    }
    # Global metadata can affect semantics; conservatively review all fixtures.
    affected = changed | (
        set(before["tables"]) | set(after["tables"]) if contract_metadata else set()
    )
    edges = {}
    for contract in (old, new):
        for child, parents in contract.dependencies().items():
            for parent in parents:
                edges.setdefault(parent, set()).add(child)
    pending = list(affected)
    while pending:
        parent = pending.pop()
        for child in edges.get(parent, set()) - affected:
            affected.add(child)
            pending.append(child)
    return {
        "old_fingerprint": old.fingerprint(),
        "new_fingerprint": new.fingerprint(),
        "changed": old.fingerprint() != new.fingerprint(),
        "changes": changes,
        "contract_metadata_changes": contract_metadata,
        "directly_changed_tables": sorted(changed),
        "affected_fixtures": sorted(affected),
        "regenerable_tables": sorted(affected & set(after["tables"])),
        "removed_tables": sorted(set(before["tables"]) - set(after["tables"])),
        "warnings": [
            "Conservative FK impact only; SQL, dashboards and application dependencies are not inferred.",
            "Regeneration must include unchanged parent fixtures or the complete dependency closure.",
            "No files, tables or fixtures were changed. Review constraints before regeneration.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", type=Path, required=True)
    parser.add_argument("--new", type=Path, required=True)
    parser.add_argument("--dialect", choices=["ansi", "spark", "databricks"], default="ansi")
    args = parser.parse_args()
    old = parse_ddl(args.old.read_text(encoding="utf-8"), dialect=args.dialect)
    new = parse_ddl(args.new.read_text(encoding="utf-8"), dialect=args.dialect)
    print(json.dumps(compare_contracts(old, new), indent=2, default=str))


if __name__ == "__main__":
    main()
