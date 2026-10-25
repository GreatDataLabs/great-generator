"""Explicit distributed checks. Actions run only when this function is called."""

from __future__ import annotations


def check_spark_keys(tables, *, primary_keys, relationships=(), non_nullable=()):
    from pyspark.sql import functions as F

    checks, counts = {}, {}

    def column(table, name):
        if not isinstance(name, str) or table not in tables or name not in tables[table].columns:
            raise ValueError(f"Missing single-column key: {table}.{name}")
        return F.col("`" + name.replace("`", "``") + "`")

    for table, frame in tables.items():
        counts[table] = frame.count()
    for table, name in primary_keys.items():
        key = column(table, name)
        frame = tables[table]
        checks[f"{table}.{name}:not_null"] = frame.filter(key.isNull()).limit(1).count() == 0
        checks[f"{table}.{name}:unique"] = (
            frame.groupBy(key).count().filter(F.col("count") > 1).limit(1).count() == 0
        )
    for table, name in non_nullable:
        key = column(table, name)
        checks[f"{table}.{name}:required"] = (
            tables[table].filter(key.isNull()).limit(1).count() == 0
        )
    for child, fk, parent, pk in relationships:
        child_key, parent_key = column(child, fk), column(parent, pk)
        children = tables[child].filter(child_key.isNotNull()).select(child_key.alias("__key"))
        parents = tables[parent].filter(parent_key.isNotNull()).select(parent_key.alias("__key"))
        checks[f"{child}.{fk}->{parent}.{pk}:fk"] = (
            children.join(parents, "__key", "left_anti").limit(1).count() == 0
        )
        checks[f"{parent}.{pk}:referenced_unique"] = (
            parents.groupBy("__key").count().filter(F.col("count") > 1).limit(1).count() == 0
        )
    return {
        "passed": bool(checks) and all(checks.values()),
        "checks": checks,
        "row_counts": counts,
        "warnings": [] if checks else ["No keys were checked."],
    }
