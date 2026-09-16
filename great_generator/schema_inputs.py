"""Schema-source ingestion helpers for optional enterprise metadata inputs.

The functions in this module normalize external schema documentation formats into
Great Generator's existing single-table schema path. They intentionally do not
introduce a second generation engine.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

UNSUPPORTED_JSON_SCHEMA_KEYWORDS = {
    "oneOf",
    "anyOf",
    "allOf",
    "not",
    "patternProperties",
    "$ref",
}


@dataclass(frozen=True)
class NormalizedSchemaInput:
    """Normalized single-table schema plus optional generation rules."""

    schema: dict[str, str]
    custom_rules: dict[str, dict[str, Any]] = field(default_factory=dict)
    required_columns: tuple[str, ...] = ()
    unique_columns: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()
    source_format: str = "schema"
    metadata: Mapping[str, Any] = field(default_factory=dict)


class SchemaInputError(ValueError):
    """Raised when a schema-source document cannot be normalized safely."""


def normalize_json_schema(
    schema: Mapping[str, Any] | str | Path,
    *,
    strict: bool = True,
    table_name: str = "sample",
) -> NormalizedSchemaInput:
    """Normalize a practical subset of JSON Schema into a generation schema."""

    payload = _read_json_payload(schema)
    if not isinstance(payload, Mapping):
        raise SchemaInputError("JSON Schema input must be a JSON object or a path to one.")

    diagnostics = _json_schema_diagnostics(payload)
    if strict and diagnostics:
        raise SchemaInputError("Unsupported JSON Schema features: " + "; ".join(diagnostics))

    schema_type = payload.get("type", "object")
    if schema_type != "object":
        raise SchemaInputError(
            "JSON Schema ingestion supports top-level type: object in this release."
        )

    properties = payload.get("properties")
    if not isinstance(properties, Mapping) or not properties:
        raise SchemaInputError("JSON Schema must define a non-empty properties object.")

    required = tuple(str(item) for item in payload.get("required", []) or [])
    columns: dict[str, str] = {}
    rules: dict[str, dict[str, Any]] = {}
    unique_columns: list[str] = []

    for column_name, raw_spec in properties.items():
        if not isinstance(raw_spec, Mapping):
            raise SchemaInputError(f"JSON Schema property '{column_name}' must be an object.")
        name = str(column_name)
        dtype = _json_schema_dtype(raw_spec)
        columns[name] = dtype
        rule = _rules_from_json_property(raw_spec)
        if rule:
            rules[name] = rule
        if bool(raw_spec.get("unique")):
            unique_columns.append(name)

    return NormalizedSchemaInput(
        schema=columns,
        custom_rules=rules,
        required_columns=required,
        unique_columns=tuple(unique_columns),
        diagnostics=tuple(diagnostics),
        source_format="json_schema",
        metadata={"title": payload.get("title"), "table_name": table_name},
    )


def normalize_dbt_schema(
    path: str | Path,
    *,
    model_name: str,
    strict: bool = True,
) -> NormalizedSchemaInput:
    """Normalize a common dbt schema.yml model entry."""

    payload = _load_yaml_file(path)
    if not isinstance(payload, Mapping):
        raise SchemaInputError("dbt schema.yml must contain a mapping with a models list.")
    models = payload.get("models")
    if not isinstance(models, Sequence) or isinstance(models, (str, bytes)):
        raise SchemaInputError("dbt schema.yml must contain a models list.")
    model = _find_named_item(models, model_name, "dbt model")
    return _normalize_dbt_model(model, model_name=model_name, source_format="dbt_schema_yml")


def normalize_dbt_manifest(
    path: str | Path,
    *,
    model_name: str,
    strict: bool = True,
) -> NormalizedSchemaInput:
    """Normalize a common dbt target/manifest.json model node."""

    del strict  # reserved for future manifest variants
    payload = _read_json_payload(path)
    if not isinstance(payload, Mapping):
        raise SchemaInputError("dbt manifest.json must contain a JSON object.")
    nodes = payload.get("nodes")
    if not isinstance(nodes, Mapping):
        raise SchemaInputError("dbt manifest.json must contain a nodes object.")

    match: Mapping[str, Any] | None = None
    for node in nodes.values():
        if not isinstance(node, Mapping):
            continue
        if node.get("resource_type") != "model":
            continue
        if node.get("name") == model_name or node.get("alias") == model_name:
            match = node
            break
    if match is None:
        raise SchemaInputError(f"Could not find dbt model '{model_name}' in manifest.")
    return _normalize_dbt_model(match, model_name=model_name, source_format="dbt_manifest")


def load_data_dictionary(path: str | Path) -> dict[str, str]:
    """Load a CSV, YAML, or JSON data dictionary as a simple ``{column: dtype}`` schema."""

    return normalize_data_dictionary(path).schema


def normalize_data_dictionary(path: str | Path) -> NormalizedSchemaInput:
    """Normalize an enterprise data dictionary from CSV, YAML, or JSON."""

    source = Path(path)
    suffix = source.suffix.lower()
    if suffix == ".csv":
        rows = _read_data_dictionary_csv(source)
    elif suffix in {".yaml", ".yml"}:
        rows = _read_data_dictionary_yaml(source)
    elif suffix == ".json":
        rows = _read_data_dictionary_json(source)
    else:
        raise SchemaInputError(
            "Data dictionary files must use .csv, .yaml, .yml, or .json extension."
        )
    return _normalize_data_dictionary_rows(rows, source=str(source))


def enforce_normalized_constraints(
    data: Any,
    normalized: NormalizedSchemaInput,
    *,
    seed: int | None = None,
) -> Any:
    """Apply lightweight post-generation constraints for schema-source wrappers.

    This is intentionally conservative and currently applies to pandas DataFrames.
    Spark outputs are returned unchanged because Spark-native arbitrary-schema
    generation already flows through the existing Spark path.
    """

    if not isinstance(data, pd.DataFrame):
        return data
    frame = data.copy()
    row_count = len(frame)
    if row_count == 0:
        return frame

    for column, rule in normalized.custom_rules.items():
        if column not in frame.columns:
            continue
        if "values" in rule:
            values = list(rule["values"])
            if values:
                frame[column] = [values[index % len(values)] for index in range(row_count)]
        if {"min", "max"} & set(rule):
            numeric = pd.to_numeric(frame[column], errors="coerce")
            lower = rule.get("min")
            upper = rule.get("max")
            if lower is not None:
                numeric = numeric.clip(lower=float(lower))
            if upper is not None:
                numeric = numeric.clip(upper=float(upper))
            if pd.api.types.is_integer_dtype(frame[column].dtype):
                frame[column] = numeric.round().astype("int64")
            elif pd.api.types.is_numeric_dtype(frame[column].dtype):
                frame[column] = numeric
        if {"min_length", "max_length"} & set(rule):
            values = frame[column].astype(str)
            max_length = rule.get("max_length")
            min_length = rule.get("min_length")
            if max_length is not None:
                values = values.str.slice(0, int(max_length))
            if min_length is not None:
                minimum_length = int(min_length)
                values = values.map(lambda item, length=minimum_length: item.ljust(length, "x"))
            frame[column] = values

    for column in normalized.unique_columns:
        if column not in frame.columns:
            continue
        frame[column] = _unique_values_for_column(frame[column], column, row_count, normalized)

    for column in normalized.required_columns:
        if column not in frame.columns:
            continue
        if frame[column].isna().any():
            frame[column] = frame[column].fillna(_fallback_value_for_column(column, normalized))
    return frame


def merge_custom_rules(
    normalized: NormalizedSchemaInput,
    custom_rules: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    """Merge source-derived rules with caller-provided rules."""

    merged = {column: dict(rule) for column, rule in normalized.custom_rules.items()}
    for column, rule in (custom_rules or {}).items():
        updated = dict(merged.get(str(column), {}))
        updated.update(dict(rule))
        merged[str(column)] = updated
    for column in normalized.unique_columns:
        merged.setdefault(column, {})["unique"] = True
    for column in normalized.required_columns:
        merged.setdefault(column, {})["null_rate"] = 0.0
    return merged


def _read_json_payload(value: Mapping[str, Any] | str | Path) -> Any:
    if isinstance(value, Mapping):
        return dict(value)
    path = Path(value)
    return json.loads(path.read_text(encoding="utf-8"))


def _json_schema_diagnostics(schema: Mapping[str, Any], path: str = "$") -> list[str]:
    diagnostics: list[str] = []
    for keyword in UNSUPPORTED_JSON_SCHEMA_KEYWORDS:
        if keyword in schema:
            diagnostics.append(f"{path}.{keyword}")
    properties = schema.get("properties")
    if isinstance(properties, Mapping):
        for name, spec in properties.items():
            if isinstance(spec, Mapping):
                diagnostics.extend(_json_schema_diagnostics(spec, f"{path}.properties.{name}"))
                if spec.get("type") == "object":
                    diagnostics.append(f"{path}.properties.{name}: nested objects are partial")
    return diagnostics


def _json_schema_dtype(spec: Mapping[str, Any]) -> str:
    json_type = spec.get("type", "string")
    if isinstance(json_type, Sequence) and not isinstance(json_type, (str, bytes)):
        non_null = [item for item in json_type if item != "null"]
        json_type = non_null[0] if non_null else "string"
    fmt = str(spec.get("format", "")).lower()
    if json_type == "integer":
        return "int"
    if json_type == "number":
        return "float"
    if json_type == "boolean":
        return "bool"
    if json_type == "array":
        return "array<string>"
    if json_type == "object":
        return "string"
    if fmt == "date":
        return "date"
    if fmt == "date-time":
        return "datetime"
    return "string"


def _rules_from_json_property(spec: Mapping[str, Any]) -> dict[str, Any]:
    rule: dict[str, Any] = {}
    if "enum" in spec:
        enum_values = spec.get("enum")
        if isinstance(enum_values, Sequence) and not isinstance(enum_values, (str, bytes)):
            rule["values"] = list(enum_values)
    if "minimum" in spec:
        rule["min"] = spec["minimum"]
    if "maximum" in spec:
        rule["max"] = spec["maximum"]
    if "minLength" in spec:
        rule["min_length"] = spec["minLength"]
    if "maxLength" in spec:
        rule["max_length"] = spec["maxLength"]
    fmt = str(spec.get("format", "")).lower()
    if fmt == "email":
        rule["type"] = "email"
    elif fmt == "date":
        rule["type"] = "generic_date"
    elif fmt == "date-time":
        rule["type"] = "datetime"
    if "default" in spec:
        rule["default"] = spec["default"]
    return rule


def _load_yaml_file(path: str | Path) -> Any:
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover - depends on optional environment
        raise ImportError(
            "YAML schema ingestion requires PyYAML. Install with "
            "pip install 'great-generator[dbt]' or 'great-generator[schema-ingest]'."
        ) from exc
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _find_named_item(items: Sequence[Any], name: str, label: str) -> Mapping[str, Any]:
    for item in items:
        if isinstance(item, Mapping) and item.get("name") == name:
            return item
    raise SchemaInputError(f"Could not find {label} '{name}'.")


def _normalize_dbt_model(
    model: Mapping[str, Any],
    *,
    model_name: str,
    source_format: str,
) -> NormalizedSchemaInput:
    columns_payload = model.get("columns")
    if isinstance(columns_payload, Mapping):
        columns_iterable = list(columns_payload.values())
    elif isinstance(columns_payload, Sequence) and not isinstance(columns_payload, (str, bytes)):
        columns_iterable = list(columns_payload)
    else:
        raise SchemaInputError(f"dbt model '{model_name}' does not define columns metadata.")

    schema: dict[str, str] = {}
    rules: dict[str, dict[str, Any]] = {}
    required: list[str] = []
    unique: list[str] = []

    for raw_column in columns_iterable:
        if not isinstance(raw_column, Mapping):
            continue
        name = raw_column.get("name")
        if not name:
            raise SchemaInputError(f"dbt model '{model_name}' has a column without a name.")
        column_name = str(name)
        dtype = _map_dtype(raw_column.get("data_type") or raw_column.get("dtype") or "string")
        schema[column_name] = dtype
        tests = raw_column.get("tests") or raw_column.get("data_tests") or []
        column_rules, is_required, is_unique = _rules_from_dbt_tests(tests)
        if column_rules:
            rules[column_name] = column_rules
        if is_required:
            required.append(column_name)
        if is_unique:
            unique.append(column_name)

    if not schema:
        raise SchemaInputError(f"dbt model '{model_name}' does not define any usable columns.")
    return NormalizedSchemaInput(
        schema=schema,
        custom_rules=rules,
        required_columns=tuple(required),
        unique_columns=tuple(unique),
        source_format=source_format,
        metadata={"model_name": model_name, "description": model.get("description")},
    )


def _rules_from_dbt_tests(tests: Any) -> tuple[dict[str, Any], bool, bool]:
    rule: dict[str, Any] = {}
    required = False
    unique = False
    if not isinstance(tests, Sequence) or isinstance(tests, (str, bytes)):
        tests = [tests]
    for test in tests:
        if test == "not_null":
            required = True
            continue
        if test == "unique":
            unique = True
            continue
        if isinstance(test, Mapping):
            if "not_null" in test:
                required = True
            if "unique" in test:
                unique = True
            accepted = test.get("accepted_values")
            if isinstance(accepted, Mapping):
                values = accepted.get("values")
                if isinstance(values, Sequence) and not isinstance(values, (str, bytes)):
                    rule["values"] = list(values)
    return rule, required, unique


def _read_data_dictionary_csv(path: Path) -> list[Mapping[str, Any]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _read_data_dictionary_yaml(path: Path) -> list[Mapping[str, Any]]:
    payload = _load_yaml_file(path)
    return _data_dictionary_rows_from_payload(payload, source=str(path))


def _read_data_dictionary_json(path: Path) -> list[Mapping[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return _data_dictionary_rows_from_payload(payload, source=str(path))


def _data_dictionary_rows_from_payload(payload: Any, *, source: str) -> list[Mapping[str, Any]]:
    if isinstance(payload, Mapping):
        for key in ("columns", "fields", "schema"):
            value = payload.get(key)
            if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
                return [item for item in value if isinstance(item, Mapping)]
        if all(isinstance(value, Mapping) for value in payload.values()):
            rows: list[Mapping[str, Any]] = []
            for column_name, spec in payload.items():
                row = dict(spec)
                row.setdefault("column_name", column_name)
                rows.append(row)
            return rows
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
        return [item for item in payload if isinstance(item, Mapping)]
    raise SchemaInputError(f"Data dictionary {source} must contain a list of columns.")


def _normalize_data_dictionary_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    source: str,
) -> NormalizedSchemaInput:
    schema: dict[str, str] = {}
    rules: dict[str, dict[str, Any]] = {}
    required: list[str] = []
    unique: list[str] = []
    metadata: dict[str, dict[str, Any]] = {}

    for index, row in enumerate(rows, start=1):
        column_name = _first_present(row, "column_name", "name", "column", "field")
        if not column_name:
            raise SchemaInputError(f"Data dictionary row {index} is missing column_name.")
        name = str(column_name)
        dtype = _map_dtype(_first_present(row, "data_type", "dtype", "type") or "string")
        schema[name] = dtype
        rule: dict[str, Any] = {}
        values = _parse_allowed_values(_first_present(row, "allowed_values", "values", "enum"))
        if values:
            rule["values"] = values
        minimum = _first_present(row, "min", "minimum", "min_value")
        maximum = _first_present(row, "max", "maximum", "max_value")
        if minimum not in (None, ""):
            rule["min"] = _maybe_number(minimum)
        if maximum not in (None, ""):
            rule["max"] = _maybe_number(maximum)
        if rule:
            rules[name] = rule
        nullable = _parse_bool(_first_present(row, "nullable", "is_nullable"))
        if nullable is False:
            required.append(name)
        if _parse_bool(_first_present(row, "unique", "primary_key", "is_unique")):
            unique.append(name)
        metadata[name] = {
            "description": row.get("description"),
            "foreign_key": row.get("foreign_key"),
            "pii_class": row.get("pii_class"),
        }

    if not schema:
        raise SchemaInputError(f"Data dictionary {source} did not define any columns.")
    return NormalizedSchemaInput(
        schema=schema,
        custom_rules=rules,
        required_columns=tuple(required),
        unique_columns=tuple(unique),
        source_format="data_dictionary",
        metadata={"source": source, "columns": metadata},
    )


def _map_dtype(value: Any) -> str:
    raw = str(value or "string").strip().lower()
    if raw.startswith("array"):
        return raw
    if raw.startswith("struct"):
        return raw
    if any(token in raw for token in ("bigint", "smallint", "integer", "int")):
        return "int"
    if any(token in raw for token in ("decimal", "numeric", "number", "double", "float", "real")):
        return "float"
    if any(token in raw for token in ("bool",)):
        return "bool"
    if any(token in raw for token in ("timestamp", "datetime")):
        return "datetime"
    if raw == "date" or raw.endswith(" date"):
        return "date"
    return "string"


def _first_present(row: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in row and row[name] not in (None, ""):
            return row[name]
    return None


def _parse_allowed_values(value: Any) -> list[Any]:
    if value in (None, ""):
        return []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return list(value)
    text = str(value).strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, Sequence) and not isinstance(parsed, (str, bytes)):
            return list(parsed)
    delimiter = "|" if "|" in text else ","
    return [item.strip() for item in text.split(delimiter) if item.strip()]


def _parse_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "t", "yes", "y", "1"}:
        return True
    if text in {"false", "f", "no", "n", "0"}:
        return False
    return None


def _maybe_number(value: Any) -> Any:
    if isinstance(value, (int, float)):
        return value
    text = str(value)
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return value


def _unique_values_for_column(
    series: pd.Series,
    column: str,
    rows: int,
    normalized: NormalizedSchemaInput,
) -> list[Any]:
    rule = normalized.custom_rules.get(column, {})
    minimum = rule.get("min", 1)
    maximum = rule.get("max")
    dtype = str(normalized.schema.get(column, "string")).lower()
    if any(token in dtype for token in ("int", "float", "double", "decimal")):
        start = int(float(minimum or 1))
        if maximum is not None and start + rows - 1 > int(float(maximum)):
            raise SchemaInputError(
                f"Cannot satisfy unique values for '{column}' within configured min/max bounds."
            )
        values = list(range(start, start + rows))
        if "float" in dtype or "double" in dtype or "decimal" in dtype:
            return [float(value) for value in values]
        return values
    if not series.dropna().duplicated().any() and not series.isna().any():
        return list(series)
    return [f"{column}_{index:06d}" for index in range(1, rows + 1)]


def _fallback_value_for_column(column: str, normalized: NormalizedSchemaInput) -> Any:
    rule = normalized.custom_rules.get(column, {})
    if "values" in rule and rule["values"]:
        return list(rule["values"])[0]
    if "default" in rule:
        return rule["default"]
    dtype = normalized.schema.get(column, "string")
    if any(token in dtype for token in ("int", "float", "double", "decimal")):
        return 0
    if "bool" in dtype:
        return False
    if "date" in dtype:
        return "2025-01-01"
    return f"{column}_value"
