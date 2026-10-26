"""Public contract-to-test compiler built on Great Generator's existing engines."""

from __future__ import annotations

import hashlib
import json
import platform
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from great_generator.contracts.ddl import parse_ddl
from great_generator.core.realism import normalize_realism_mode, validate_realism
from great_generator.engines.pandas_engine import generate_domain as generate_with_pandas
from great_generator.schemas.models import ContractSchema, DomainSchema
from great_generator.schemas.relational import relational_schema_from_specs
from great_generator.testing.constraint_planner import (
    DEFAULT_COVERAGE,
    plan_coverage_scenarios,
)
from great_generator.testing.query_contract import CoverageScenario, WorkloadContract
from great_generator.testing.reports import (
    build_coverage_report,
    expected_result_assertions,
    write_static_html_report,
)
from great_generator.testing.scenario_generator import materialize_scenarios
from great_generator.testing.scenario_validator import validate_test_dataset
from great_generator.testing.workload_parser import parse_sql_workload


@dataclass
class ContractTestResult:
    """Generated datasets plus measured workload-coverage artifacts."""

    datasets: dict[str, pd.DataFrame]
    negative_datasets: dict[str, dict[str, pd.DataFrame]]
    schema: DomainSchema
    workload: WorkloadContract
    scenarios: list[CoverageScenario]
    row_counts: dict[str, int]
    requested_coverage: tuple[str, ...]
    validation_report: dict[str, Any]
    coverage_report_data: dict[str, Any]
    expected_results: list[dict[str, Any]]
    manifest: dict[str, Any]
    planner_warnings: list[str]

    def validate(self) -> dict[str, Any]:
        """Re-run clean-data, relationship, row-count, and witness validation."""

        self.validation_report = validate_test_dataset(
            self.datasets,
            self.schema,
            self.row_counts,
            self.workload,
            self.scenarios,
        )
        self.coverage_report_data = build_coverage_report(
            workload=self.workload,
            schema=self.schema,
            scenarios=self.scenarios,
            validation=self.validation_report,
            coverage=self.requested_coverage,
            planner_warnings=self.planner_warnings,
            negative_cases=self.negative_datasets,
        )
        self.expected_results = expected_result_assertions(self.validation_report)
        return self.validation_report

    def coverage_report(self) -> dict[str, Any]:
        """Return machine-readable coverage with explicit denominators."""

        return _jsonable(self.coverage_report_data)

    def generate_report(self, *, format: str = "json", output: str | Path) -> Path:
        """Write a static JSON or HTML report without embedding generated records."""

        normalized = format.lower().strip()
        payload = {
            "coverage": self.coverage_report_data,
            "validation": self.validation_report,
            "expected_results": self.expected_results,
            "manifest": self.manifest,
        }
        target = Path(output)
        if normalized == "html":
            return write_static_html_report(payload, target)
        if normalized != "json":
            raise ValueError("Report format must be 'json' or 'html'.")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(_jsonable(payload), indent=2), encoding="utf-8")
        return target

    def export(
        self,
        output: str | Path,
        *,
        format: str = "parquet",
        overwrite: bool = False,
    ) -> Path:
        """Export datasets and reproducibility artifacts to a reviewable directory."""

        normalized = format.lower().strip()
        if normalized not in {"parquet", "csv", "json"}:
            raise ValueError("Export format must be 'parquet', 'csv', or 'json'.")
        root = Path(output)
        if root.exists() and any(root.iterdir()) and not overwrite:
            raise FileExistsError(
                f"Output directory '{root}' is not empty. Pass overwrite=True to replace files."
            )
        root.mkdir(parents=True, exist_ok=True)
        _write_frames(self.datasets, root / "datasets", normalized)
        for case_name, frames in self.negative_datasets.items():
            _write_frames(frames, root / "negative_cases" / case_name, normalized)
        _write_json(root / "query_contract.json", self.workload.to_dict())
        _write_json(root / "scenarios.json", [item.to_dict() for item in self.scenarios])
        _write_json(root / "expected_results.json", self.expected_results)
        _write_json(root / "coverage_report.json", self.coverage_report_data)
        _write_json(root / "validation_report.json", self.validation_report)
        _write_json(root / "generation_manifest.json", self.manifest)
        return root


def compile_test_dataset(
    schema: DomainSchema | ContractSchema | Mapping[str, Any] | str | Path,
    queries: str | Path | Sequence[str | Path],
    *,
    rows: Mapping[str, int] | int = 100,
    coverage: Sequence[str] | None = None,
    engine: str = "pandas",
    seed: int | None = None,
    relationships: Sequence[str | Mapping[str, str]] | None = None,
    dialect: str | None = None,
    realism: str = "realistic",
    generate_expected_results: bool = True,
) -> ContractTestResult:
    """Compile schema and SQL requirements into deterministic synthetic test data.

    Phase 1 deliberately supports the Pandas engine. Spark-native workload scenario
    materialization is a later gated phase; requesting it fails clearly rather than
    collecting a large Spark dataset on the driver.
    """

    if engine != "pandas":
        raise NotImplementedError(
            "compile_test_dataset currently supports engine='pandas'. Spark-native "
            "coverage scenario materialization is planned for the Spark phase and does "
            "not fall back to driver-side Pandas generation."
        )
    realism = normalize_realism_mode(realism)
    validate_realism(realism)
    normalized_schema, row_counts = _normalize_schema(
        schema, rows=rows, relationships=relationships
    )
    workload = parse_sql_workload(queries, schema=normalized_schema, dialect=dialect)
    requested_coverage = tuple(dict.fromkeys(coverage or DEFAULT_COVERAGE))
    scenarios, planner_warnings = plan_coverage_scenarios(
        workload,
        normalized_schema,
        coverage=requested_coverage,
    )
    _validate_witness_capacity(workload, scenarios, row_counts)

    baseline = generate_with_pandas(
        domain_module=None,
        schema=normalized_schema,
        row_counts=row_counts,
        seed=seed,
        anomalies=None,
        realism=realism,
        return_labels=False,
    )
    datasets, materialized = materialize_scenarios(
        baseline,
        normalized_schema,
        workload,
        scenarios,
    )
    negative_datasets = (
        _negative_cases(datasets, normalized_schema)
        if "negative_cases" in requested_coverage
        else {}
    )
    validation = validate_test_dataset(
        datasets,
        normalized_schema,
        row_counts,
        workload,
        materialized,
    )
    coverage_report = build_coverage_report(
        workload=workload,
        schema=normalized_schema,
        scenarios=materialized,
        validation=validation,
        coverage=requested_coverage,
        planner_warnings=planner_warnings,
        negative_cases=negative_datasets,
    )
    expected = expected_result_assertions(validation) if generate_expected_results else []
    manifest = _manifest(
        schema=normalized_schema,
        workload=workload,
        scenarios=materialized,
        seed=seed,
        engine=engine,
        rows=row_counts,
    )
    return ContractTestResult(
        datasets=datasets,
        negative_datasets=negative_datasets,
        schema=normalized_schema,
        workload=workload,
        scenarios=materialized,
        row_counts=row_counts,
        requested_coverage=requested_coverage,
        validation_report=validation,
        coverage_report_data=coverage_report,
        expected_results=expected,
        manifest=manifest,
        planner_warnings=planner_warnings,
    )


def _normalize_schema(
    source: DomainSchema | ContractSchema | Mapping[str, Any] | str | Path,
    *,
    rows: Mapping[str, int] | int,
    relationships: Sequence[str | Mapping[str, str]] | None,
) -> tuple[DomainSchema, dict[str, int]]:
    if isinstance(source, ContractSchema):
        domain = source.to_domain_schema(name=source.name)
        return domain, _row_counts(domain, rows)
    if isinstance(source, DomainSchema):
        return source, _row_counts(source, rows)

    loaded = _load_schema_source(source)
    if isinstance(loaded, ContractSchema):
        domain = loaded.to_domain_schema(name=loaded.name)
        return domain, _row_counts(domain, rows)
    if not isinstance(loaded, Mapping):
        raise TypeError(
            "schema must be a DomainSchema, ContractSchema, table mapping, SQL DDL, "
            "or JSON/YAML contract path."
        )
    table_specs = loaded.get("tables", loaded)
    if not isinstance(table_specs, Mapping):
        raise ValueError("A contract mapping must contain a 'tables' mapping.")
    declared_relationships = relationships
    if declared_relationships is None and "tables" in loaded:
        raw_relationships = loaded.get("relationships")
        if raw_relationships is not None:
            if not isinstance(raw_relationships, Sequence) or isinstance(
                raw_relationships, (str, bytes)
            ):
                raise ValueError("Contract 'relationships' must be a sequence.")
            declared_relationships = raw_relationships
    return relational_schema_from_specs(
        tables=table_specs,
        rows=rows,
        relationships=declared_relationships,
        name=(
            str(loaded.get("name", "contract_to_test"))
            if "tables" in loaded
            else "contract_to_test"
        ),
    )


def _load_schema_source(source: Mapping[str, Any] | str | Path) -> Any:
    if isinstance(source, Mapping):
        return source
    path = Path(source)
    try:
        is_file = path.is_file()
    except OSError:
        is_file = False
    if is_file:
        text = path.read_text(encoding="utf-8")
        suffix = path.suffix.lower()
        if suffix == ".sql":
            return parse_ddl(text)
        if suffix == ".json":
            return json.loads(text)
        if suffix in {".yaml", ".yml"}:
            try:
                import yaml
            except ImportError as exc:  # pragma: no cover - environment dependent
                raise ImportError(
                    'YAML contracts require PyYAML. Install with pip install "great-generator[schema-ingest]".'
                ) from exc
            payload = yaml.safe_load(text)
            if not isinstance(payload, Mapping):
                raise ValueError(f"YAML contract '{path}' must contain a mapping.")
            return payload
        raise ValueError("Schema files must use .sql, .json, .yaml, or .yml.")
    text = str(source).strip()
    if "create table" in text.lower():
        return parse_ddl(text)
    raise ValueError(
        "String schema input must be SQL CREATE TABLE DDL or an existing contract file path."
    )


def _row_counts(schema: DomainSchema, rows: Mapping[str, int] | int) -> dict[str, int]:
    if isinstance(rows, Mapping):
        unknown = sorted(set(rows) - set(schema.tables))
        if unknown:
            raise ValueError(f"rows references unknown tables: {unknown}.")
        counts = {name: int(rows.get(name, 100)) for name in schema.tables}
    else:
        counts = {name: int(rows) for name in schema.tables}
    if any(value < 0 for value in counts.values()):
        raise ValueError("rows must be greater than or equal to zero.")
    return counts


def _validate_witness_capacity(
    workload: WorkloadContract,
    scenarios: Sequence[CoverageScenario],
    row_counts: Mapping[str, int],
) -> None:
    queries = {query.query_id: query for query in workload.queries}
    required: dict[str, int] = {table: 0 for table in row_counts}
    for scenario in scenarios:
        for table in queries[scenario.query_id].tables:
            required[table] = required.get(table, 0) + 1
    insufficient = {
        table: {"required": count, "configured": int(row_counts.get(table, 0))}
        for table, count in required.items()
        if count > int(row_counts.get(table, 0))
    }
    if insufficient:
        raise ValueError(
            "The requested row counts cannot hold distinct coverage witnesses: "
            f"{insufficient}. Increase rows or request fewer coverage targets."
        )


def _negative_cases(
    data: Mapping[str, pd.DataFrame], schema: DomainSchema
) -> dict[str, dict[str, pd.DataFrame]]:
    cases: dict[str, dict[str, pd.DataFrame]] = {}
    for child_table, table in schema.tables.items():
        if not table.foreign_keys or data[child_table].empty:
            continue
        foreign_key = table.foreign_keys[0]
        frames = _copy_frames(data)
        child_column = foreign_key.child_columns[0]
        parent_column = foreign_key.parent_columns[0]
        frames[child_table].iat[0, frames[child_table].columns.get_loc(child_column)] = (
            _orphan_value(data[foreign_key.parent_table][parent_column])
        )
        cases["missing_foreign_key"] = frames
        break

    for table_name, table in schema.tables.items():
        candidates = [
            column
            for column in table.columns
            if not column.nullable and column.name not in table.primary_key_columns
        ]
        if candidates and not data[table_name].empty:
            frames = _copy_frames(data)
            column = candidates[0].name
            frames[table_name].iat[0, frames[table_name].columns.get_loc(column)] = None
            cases["unexpected_null"] = frames
            break
    return cases


def _orphan_value(series: pd.Series) -> Any:
    if pd.api.types.is_numeric_dtype(series.dtype):
        maximum = series.dropna().max()
        return int(maximum) + 1_000_003 if maximum is not None else 1_000_003
    return "__GG_INTENTIONAL_ORPHAN__"


def _copy_frames(data: Mapping[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {name: frame.copy(deep=True) for name, frame in data.items()}


def _manifest(
    *,
    schema: DomainSchema,
    workload: WorkloadContract,
    scenarios: Sequence[CoverageScenario],
    seed: int | None,
    engine: str,
    rows: Mapping[str, int],
) -> dict[str, Any]:
    from great_generator import __version__

    schema_payload = schema.as_dict()
    workload_payload = workload.to_dict()
    scenario_payload = [scenario.to_dict() for scenario in scenarios]
    return {
        "project": "great-generator",
        "version": __version__,
        "synthetic": True,
        "manifest_version": "1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generation": {
            "seed": seed,
            "rows": dict(rows),
            "schema_contract_hash": _hash(schema_payload),
            "workload_contract_hash": _hash(workload_payload),
            "scenario_plan_hash": _hash(scenario_payload),
        },
        "environment": {
            "python_version": platform.python_version(),
            "execution_engine": engine,
            "engine_version": pd.__version__,
            "platform": platform.platform(),
        },
        "source_data_read": False,
        "records_embedded_in_manifest": False,
    }


def _hash(payload: Any) -> str:
    encoded = json.dumps(_jsonable(payload), sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _write_frames(data: Mapping[str, pd.DataFrame], root: Path, format: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for table_name, frame in data.items():
        path = root / f"{table_name}.{format}"
        if format == "parquet":
            frame.to_parquet(path, index=False)
        elif format == "csv":
            frame.to_csv(path, index=False)
        else:
            frame.to_json(path, orient="records", lines=True, date_format="iso")


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(_jsonable(payload), indent=2), encoding="utf-8")


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    return value
