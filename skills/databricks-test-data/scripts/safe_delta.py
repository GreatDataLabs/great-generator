"""Small opt-in Delta writer; caller must obtain real approval, not infer it from a name."""

from __future__ import annotations

import re
from urllib.parse import urlsplit


def validate_target(target, kind):
    if not isinstance(target, str) or not target.strip():
        raise ValueError("An explicit Delta target is required.")
    if kind == "table":
        if not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*", target
        ):
            raise ValueError("Use an unquoted catalog.schema.table test target.")
    elif kind == "path":
        parts = urlsplit(target)
        if (
            parts.query
            or parts.fragment
            or "%" in target
            or "\\" in target
            or ".." in target.split("/")
        ):
            raise ValueError(
                "Use a literal output path without traversal, query strings or fragments."
            )
        cloud = (
            parts.scheme in {"s3", "gs", "abfss"}
            and bool(parts.netloc)
            and bool(parts.path.strip("/"))
        )
        dbfs = target.startswith("dbfs:/") and bool(target[len("dbfs:/") :].strip("/"))
        volume = target.startswith("/Volumes/") and len(target.strip("/").split("/")) >= 5
        if not (cloud or dbfs or volume):
            raise ValueError(
                "Use a dedicated dbfs:/, /Volumes/.../dataset, s3://, abfss:// or gs:// path."
            )
    else:
        raise ValueError("kind must be 'table' or 'path'.")
    return target


def write_delta(
    df,
    target,
    *,
    kind="table",
    approved_target=None,
    mode="errorifexists",
    partition_by=(),
    overwrite_confirmed=False,
):
    """Write only on an explicit call; approval evidence must come from the user.

    This is an example guardrail, not an authorization system. Verify permissions,
    test ownership and existing schema separately. No schema evolution is enabled.
    """
    validate_target(target, kind)
    if approved_target != target:
        raise ValueError("Obtain approval for the exact destination before writing.")
    if mode not in {"errorifexists", "append", "overwrite"}:
        raise ValueError("mode must be errorifexists, append or overwrite.")
    if mode == "overwrite" and not overwrite_confirmed:
        raise ValueError("Overwrite requires explicit confirmation of data replacement.")
    if isinstance(partition_by, str) or any(c not in df.columns for c in partition_by):
        raise ValueError("partition_by must be a sequence of existing column names.")
    writer = df.write.format("delta").mode(mode)
    if partition_by:
        writer = writer.partitionBy(*partition_by)
    if kind == "table":
        writer.saveAsTable(target)
    else:
        writer.save(target)
    return {"target": target, "kind": kind, "mode": mode, "partition_by": list(partition_by)}
