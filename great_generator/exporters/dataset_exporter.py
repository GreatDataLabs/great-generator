"""Convenience dataset export helper with overwrite protection.

This module intentionally stays lightweight. Local pandas exports work with the base
package. Cloud URL exports use pandas plus optional fsspec-backed filesystems when the
caller installs the ``great-generator[cloud]`` extra and configures credentials in the
runtime environment.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from great_generator.exporters.spark_options import apply_writer_options, prepare_spark_frame

SUPPORTED_DATASET_FORMATS = {"csv", "jsonl", "parquet"}
CLOUD_PREFIXES = ("s3://", "s3a://", "s3n://", "abfs://", "abfss://", "gs://", "gcs://")


def export_dataset(
    data: Any,
    path: str | Path,
    *,
    format: str = "parquet",
    mode: str = "error",
    overwrite: bool = False,
    engine: str = "auto",
    partition_by: Sequence[str] | None = None,
    writer_options: Mapping[str, str] | None = None,
    num_partitions: int | None = None,
    partition_strategy: str = "repartition",
) -> list[str]:
    """Export one DataFrame or a mapping of table-name DataFrames.

    Parameters
    ----------
    data:
        A pandas DataFrame, Spark DataFrame, or mapping of table names to DataFrames.
    path:
        Local path or optional fsspec-compatible cloud URL. For a single pandas
        DataFrame, a missing file extension is appended. For mappings, each table is
        written under ``path/<table>/<table>.<extension>`` for pandas, or under
        ``path/<table>`` for Spark.
    format:
        One of ``"csv"``, ``"jsonl"``, or ``"parquet"``.
    mode / overwrite:
        Existing outputs are rejected by default. Pass ``overwrite=True`` or
        ``mode="overwrite"`` to replace them. Spark exports use Spark writer modes.

    Returns
    -------
    list[str]
        The file or directory locations written.
    """

    format_name = _normalize_format(format)
    allow_overwrite = overwrite or mode == "overwrite"
    if mode not in {"error", "errorifexists", "fail", "overwrite"}:
        raise ValueError("mode must be one of 'error', 'errorifexists', 'fail', or 'overwrite'.")

    tables = _as_table_mapping(data)
    resolved_engine = _resolve_engine(tables, engine)
    base_path = str(path)

    written: list[str] = []
    multi_table = isinstance(data, Mapping)
    for table_name, frame in tables.items():
        if resolved_engine == "spark":
            location = _spark_table_location(base_path, table_name, multi_table=multi_table)
            _write_spark_frame(
                frame,
                location,
                format_name,
                overwrite=allow_overwrite,
                partition_by=partition_by,
                writer_options=writer_options,
                num_partitions=num_partitions,
                partition_strategy=partition_strategy,
            )
        else:
            location = _pandas_file_location(
                base_path,
                table_name,
                format_name,
                multi_table=multi_table,
            )
            _write_pandas_frame(frame, location, format_name, overwrite=allow_overwrite)
        written.append(location)
    return written


def _normalize_format(format: str) -> str:
    format_name = format.lower().strip()
    aliases = {"json": "jsonl", "ndjson": "jsonl"}
    format_name = aliases.get(format_name, format_name)
    if format_name not in SUPPORTED_DATASET_FORMATS:
        raise ValueError(
            f"Unsupported export format '{format}'. Expected one of {sorted(SUPPORTED_DATASET_FORMATS)}."
        )
    return format_name


def _as_table_mapping(data: Any) -> dict[str, Any]:
    if isinstance(data, Mapping):
        if not data:
            raise ValueError("export_dataset requires at least one table when data is a mapping.")
        return {str(name): frame for name, frame in data.items()}
    return {"data": data}


def _resolve_engine(tables: Mapping[str, Any], engine: str) -> str:
    if engine not in {"auto", "pandas", "spark"}:
        raise ValueError("engine must be one of 'auto', 'pandas', or 'spark'.")
    if engine != "auto":
        return engine
    return "spark" if any(_is_spark_dataframe(frame) for frame in tables.values()) else "pandas"


def _is_spark_dataframe(value: Any) -> bool:
    module = value.__class__.__module__
    return module.startswith("pyspark.") and hasattr(value, "write") and hasattr(value, "schema")


def _extension(format_name: str) -> str:
    return "jsonl" if format_name == "jsonl" else format_name


def _is_cloud_path(path: str) -> bool:
    return path.lower().startswith(CLOUD_PREFIXES)


def _join_url(base: str, *parts: str) -> str:
    return "/".join([base.rstrip("/"), *[part.strip("/") for part in parts if part]])


def _pandas_file_location(
    base_path: str, table_name: str, format_name: str, *, multi_table: bool
) -> str:
    ext = _extension(format_name)
    if _is_cloud_path(base_path):
        if multi_table:
            return _join_url(base_path, table_name, f"{table_name}.{ext}")
        if Path(base_path).suffix:
            return base_path
        return f"{base_path.rstrip('/')}.{ext}"

    base = Path(base_path)
    if multi_table:
        return str(base / table_name / f"{table_name}.{ext}")
    if base.suffix:
        return str(base)
    return str(base.with_suffix(f".{ext}"))


def _spark_table_location(base_path: str, table_name: str, *, multi_table: bool) -> str:
    if multi_table:
        if _is_cloud_path(base_path):
            return _join_url(base_path, table_name)
        return str(Path(base_path) / table_name)
    return base_path


def _write_pandas_frame(frame: Any, location: str, format_name: str, *, overwrite: bool) -> None:
    if not isinstance(frame, pd.DataFrame):
        raise ValueError("pandas export requires pandas DataFrame inputs.")
    if _is_cloud_path(location):
        _write_pandas_cloud(frame, location, format_name, overwrite=overwrite)
        return

    target = Path(location)
    if target.exists() and not overwrite:
        raise FileExistsError(
            f"Output path already exists: {target}. Pass overwrite=True or mode='overwrite'."
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    if format_name == "csv":
        frame.to_csv(target, index=False)
    elif format_name == "jsonl":
        frame.to_json(target, orient="records", lines=True, date_format="iso")
    else:
        frame.to_parquet(target, index=False)


def _write_pandas_cloud(
    frame: pd.DataFrame, location: str, format_name: str, *, overwrite: bool
) -> None:
    try:
        import fsspec
    except ImportError as exc:  # pragma: no cover - exercised only without optional extra
        raise ImportError(
            "Cloud URL exports require optional dependencies. Install with "
            '`pip install "great-generator[cloud]"` and configure credentials in your runtime.'
        ) from exc

    fs, fs_path = fsspec.core.url_to_fs(location)
    if fs.exists(fs_path) and not overwrite:
        raise FileExistsError(
            f"Output path already exists: {location}. Pass overwrite=True or mode='overwrite'."
        )
    parent = fs_path.rsplit("/", 1)[0] if "/" in fs_path else ""
    if parent:
        fs.makedirs(parent, exist_ok=True)
    write_mode = "wb" if format_name == "parquet" else "wt"
    with fs.open(fs_path, write_mode) as handle:
        if format_name == "csv":
            frame.to_csv(handle, index=False)
        elif format_name == "jsonl":
            frame.to_json(handle, orient="records", lines=True, date_format="iso")
        else:
            frame.to_parquet(handle, index=False)


def _write_spark_frame(
    frame: Any,
    location: str,
    format_name: str,
    *,
    overwrite: bool,
    partition_by: Sequence[str] | None,
    writer_options: Mapping[str, str] | None,
    num_partitions: int | None,
    partition_strategy: str,
) -> None:
    if not _is_spark_dataframe(frame):
        raise ValueError("spark export requires Spark DataFrame inputs.")
    prepared = prepare_spark_frame(frame, num_partitions, partition_strategy)
    mode = "overwrite" if overwrite else "errorifexists"
    writer = apply_writer_options(prepared.write.mode(mode), writer_options)
    if format_name == "csv":
        writer.option("header", True).csv(location)
    elif format_name == "jsonl":
        writer.json(location)
    else:
        if partition_by:
            existing = [column for column in partition_by if column in prepared.columns]
            if existing:
                writer = writer.partitionBy(*existing)
        writer.parquet(location)
