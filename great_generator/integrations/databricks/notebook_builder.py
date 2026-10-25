"""Safe, review-first Databricks notebook generation for UC-derived data."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .generation import build_uc_generation_manifest, inspect_unity_catalog_table
from .models import UnityCatalogTableName, quote_identifier


def generate_uc_ingestion_code(
    source_table: str,
    *,
    include_related: bool = True,
    target_catalog: str,
    target_schema: str,
    rows: Mapping[str, int] | int = 100,
    format: str = "delta",
    output: str = "databricks_notebook",
    output_path: str | Path,
    execute: bool = False,
    seed: int | None = None,
    relationship_strategy: str = "declared",
    client: Any | None = None,
    spark: Any | None = None,
    warehouse_id: str | None = None,
    workspace_client: Any | None = None,
) -> dict[str, Path]:
    """Create a notebook and review artifacts without executing writes.

    The generated notebook contains a disabled write section. Users must review it,
    set ``ENABLE_WRITES = True``, and run that cell deliberately.
    """

    if execute:
        raise ValueError(
            "generate_uc_ingestion_code never executes writes. Generate the notebook with "
            "execute=False, review it, and enable its write cell explicitly."
        )
    if output != "databricks_notebook":
        raise ValueError("output must be 'databricks_notebook'.")
    if format not in {"delta", "parquet"}:
        raise ValueError("format must be 'delta' or 'parquet'.")
    source = UnityCatalogTableName.parse(source_table)
    target_catalog = _identifier_part(target_catalog, "target_catalog")
    target_schema = _identifier_part(target_schema, "target_schema")
    if (source.catalog.casefold(), source.schema.casefold()) == (
        target_catalog.casefold(),
        target_schema.casefold(),
    ):
        raise ValueError(
            "The synthetic target catalog/schema must differ from the source catalog/schema."
        )
    snapshot = inspect_unity_catalog_table(
        source,
        include_related=include_related,
        related_direction="parents",
        client=client,
        spark=spark,
        warehouse_id=warehouse_id,
        workspace_client=workspace_client,
    )
    destination = Path(output_path)
    if destination.suffix.lower() != ".ipynb":
        raise ValueError("output_path must end with '.ipynb'.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    row_counts = _row_counts(rows, snapshot)
    targets = {
        metadata.name.table: f"{target_catalog}.{target_schema}.{metadata.name.table}"
        for metadata in snapshot.tables.values()
    }
    validation = {"passed": None, "status": "not_run", "reason": "generated code only"}
    manifest = build_uc_generation_manifest(
        snapshot=snapshot,
        mode="relational" if include_related else "single_table",
        relationship_strategy=relationship_strategy,
        output="spark",
        row_counts=row_counts,
        seed=seed,
        validation=validation,
        output_targets=targets,
    )
    notebook = _build_notebook(
        source=source,
        include_related=include_related,
        target_catalog=target_catalog,
        target_schema=target_schema,
        rows=row_counts,
        format=format,
        seed=seed,
        relationship_strategy=relationship_strategy,
    )
    destination.write_text(json.dumps(notebook, indent=2) + "\n", encoding="utf-8")
    artifacts = {
        "notebook": destination,
        "generation_config": destination.parent / "generation_config.yaml",
        "relationships": destination.parent / "relationships.json",
        "schema_snapshot": destination.parent / "schema_snapshot.json",
        "validation_report": destination.parent / "validation_report.json",
        "generation_manifest": destination.parent / "generation_manifest.json",
    }
    artifacts["generation_config"].write_text(
        json.dumps(
            {
                "source_table": source.qualified_name,
                "include_related": include_related,
                "relationship_strategy": relationship_strategy,
                "target_catalog": target_catalog,
                "target_schema": target_schema,
                "rows": row_counts,
                "format": format,
                "seed": seed,
                "execute": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    artifacts["relationships"].write_text(
        json.dumps(
            [
                {
                    "child_table": item.child_table,
                    "child_columns": list(item.child_columns),
                    "parent_table": item.parent_table,
                    "parent_columns": list(item.parent_columns),
                    "source": item.source,
                }
                for item in snapshot.relationships
            ],
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    snapshot.save(artifacts["schema_snapshot"])
    artifacts["validation_report"].write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    artifacts["generation_manifest"].write_text(
        json.dumps(manifest, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return artifacts


def _build_notebook(
    *,
    source: UnityCatalogTableName,
    include_related: bool,
    target_catalog: str,
    target_schema: str,
    rows: Mapping[str, int],
    format: str,
    seed: int | None,
    relationship_strategy: str,
) -> dict[str, Any]:
    target_namespace = f"{quote_identifier(target_catalog)}.{quote_identifier(target_schema)}"
    config = {
        "source_table": source.qualified_name,
        "include_related": include_related,
        "relationship_strategy": relationship_strategy,
        "rows": dict(rows),
        "seed": seed,
    }
    cells = [
        _markdown(
            "# Great Generator — Unity Catalog synthetic pipeline\n\n"
            "This notebook reads **metadata only** from Unity Catalog, generates synthetic "
            "Spark DataFrames, validates relationships, and keeps all writes disabled until "
            "you explicitly approve the target cell. It never writes to the source table."
        ),
        _markdown(
            "## Prerequisites\n\n"
            "- `USE CATALOG`, `USE SCHEMA`, and metadata visibility for the source objects.\n"
            "- `CREATE`/`MODIFY` permissions only on the approved synthetic target if writes "
            "are enabled.\n"
            '- Install with `%pip install "great-generator[databricks]"`. Restart Python '
            "if your Databricks runtime requires it."
        ),
        _code(
            "from great_generator import (\n"
            "    generate_relational_from_unity_catalog,\n"
            "    inspect_unity_catalog_table,\n"
            ")\n\n"
            f"CONFIG = {json.dumps(config, indent=2)}\n"
            f"TARGET_CATALOG = {target_catalog!r}\n"
            f"TARGET_SCHEMA = {target_schema!r}\n"
            "ENABLE_WRITES = False  # review every target before changing this\n"
        ),
        _markdown("## Inspect schema and relationships"),
        _code(
            "snapshot = inspect_unity_catalog_table(\n"
            "    CONFIG['source_table'],\n"
            "    include_related=CONFIG['include_related'],\n"
            "    related_direction='parents',\n"
            "    spark=spark,\n"
            ")\n"
            "display(snapshot.as_dict())"
        ),
        _markdown("## Generate parent tables before dependent tables"),
        _code(
            "datasets, report = generate_relational_from_unity_catalog(\n"
            "    table=CONFIG['source_table'],\n"
            "    include_related=CONFIG['include_related'],\n"
            "    relationship_strategy=CONFIG['relationship_strategy'],\n"
            "    rows=CONFIG['rows'],\n"
            "    output='spark',\n"
            "    spark=spark,\n"
            "    seed=CONFIG['seed'],\n"
            "    return_report=True,\n"
            ")\n"
            "display(report['validation'])"
        ),
        _markdown("## Preview synthetic output"),
        _code(
            "for table_name, frame in datasets.items():\n"
            "    print(f'{table_name}: {frame.count():,} synthetic rows')\n"
            "    display(frame.limit(10))"
        ),
        _markdown(
            "## Review and explicitly enable sandbox writes\n\n"
            "Writes use `errorifexists`; no existing table is overwritten. The target namespace "
            "is separate from the source namespace."
        ),
        _code(
            "if not ENABLE_WRITES:\n"
            "    print('Writes are disabled. Review TARGET_CATALOG, TARGET_SCHEMA, and tables.')\n"
            "else:\n"
            f"    spark.sql('CREATE SCHEMA IF NOT EXISTS {target_namespace}')\n"
            "    for table_name, frame in datasets.items():\n"
            "        safe_table = table_name.replace('`', '``')\n"
            "        target = f'`{TARGET_CATALOG}`.`{TARGET_SCHEMA}`.`{safe_table}`'\n"
            f"        frame.write.format({format!r}).mode('errorifexists').saveAsTable(target)\n"
            "        print(f'Created synthetic table {target}')"
        ),
        _markdown(
            "## Cleanup\n\n"
            "Cleanup is intentionally not automated. Remove only the reviewed synthetic tables "
            "you created in the approved target namespace, following your workspace policy."
        ),
        _markdown(
            "## Limitations\n\n"
            "The generated data is synthetic, not anonymized production data. Unity Catalog "
            "constraints are metadata and may be incomplete because of permissions. Complex "
            "types, cyclic/self-referencing relationships, and automatic dimensional-role "
            "transformation require explicit modeling in this release."
        ),
    ]
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3"},
            "great_generator": {
                "synthetic": True,
                "metadata_only_source_read": True,
                "writes_enabled_by_default": False,
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def _row_counts(rows: Mapping[str, int] | int, snapshot: Any) -> dict[str, int]:
    if isinstance(rows, Mapping):
        result: dict[str, int] = {}
        for table in snapshot.tables.values():
            result[table.name.table] = int(
                rows.get(table.name.table, rows.get(table.qualified_name, 100))
            )
        return result
    return {table.name.table: int(rows) for table in snapshot.tables.values()}


def _identifier_part(value: str, label: str) -> str:
    text = str(value).strip()
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", text) is None:
        raise ValueError(
            f"{label} must be one non-empty identifier containing letters, digits, or "
            "underscores, and it cannot start with a digit."
        )
    return text


def _markdown(source: str) -> dict[str, Any]:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(True)}


def _code(source: str) -> dict[str, Any]:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(True),
    }
