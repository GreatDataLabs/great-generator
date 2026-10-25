"""Serializable Unity Catalog metadata models.

The models in this module contain metadata only. They never contain source table
records or Databricks credentials.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from great_generator.schemas.models import (
    CheckConstraint,
    ColumnSpec,
    ForeignKey,
    TableSchema,
    UniqueConstraint,
)


def utc_now_iso() -> str:
    """Return a UTC timestamp suitable for manifests and snapshots."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True, order=True)
class UnityCatalogTableName:
    """A validated, fully qualified Unity Catalog table name."""

    catalog: str
    schema: str
    table: str

    @classmethod
    def parse(cls, value: str | UnityCatalogTableName) -> UnityCatalogTableName:
        if isinstance(value, cls):
            return value
        parts = _split_qualified_identifier(str(value))
        if len(parts) != 3:
            raise ValueError(
                "Unity Catalog tables must use a three-part name: " "'<catalog>.<schema>.<table>'."
            )
        return cls(*parts)

    @property
    def qualified_name(self) -> str:
        return f"{self.catalog}.{self.schema}.{self.table}"

    @property
    def quoted_name(self) -> str:
        return ".".join(quote_identifier(part) for part in self.parts)

    @property
    def parts(self) -> tuple[str, str, str]:
        return self.catalog, self.schema, self.table

    def __str__(self) -> str:
        return self.qualified_name


@dataclass(frozen=True)
class UCColumnMetadata:
    """Normalized Unity Catalog column metadata."""

    name: str
    position: int
    data_type: str
    full_data_type: str | None = None
    nullable: bool = True
    description: str = ""
    default_expression: str | None = None
    generated_expression: str | None = None
    identity: bool = False
    partition_index: int | None = None
    precision: int | None = None
    scale: int | None = None
    max_length: int | None = None
    tags: Mapping[str, str] = field(default_factory=dict)
    properties: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> UCColumnMetadata:
        return cls(
            name=str(payload["name"]),
            position=int(payload.get("position", 0)),
            data_type=str(payload.get("data_type", "string")),
            full_data_type=_optional_text(payload.get("full_data_type")),
            nullable=bool(payload.get("nullable", True)),
            description=str(payload.get("description", "") or ""),
            default_expression=_optional_text(payload.get("default_expression")),
            generated_expression=_optional_text(payload.get("generated_expression")),
            identity=bool(payload.get("identity", False)),
            partition_index=_optional_int(payload.get("partition_index")),
            precision=_optional_int(payload.get("precision")),
            scale=_optional_int(payload.get("scale")),
            max_length=_optional_int(payload.get("max_length")),
            tags={str(key): str(value) for key, value in dict(payload.get("tags") or {}).items()},
            properties=dict(payload.get("properties") or {}),
        )


@dataclass(frozen=True)
class UCConstraintMetadata:
    """Primary, unique, foreign-key, or check constraint metadata."""

    name: str
    constraint_type: str
    columns: tuple[str, ...]
    referenced_table: str | None = None
    referenced_columns: tuple[str, ...] = ()
    expression: str | None = None
    enforced: bool | None = None
    on_update: str | None = None
    on_delete: str | None = None
    properties: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> UCConstraintMetadata:
        return cls(
            name=str(payload.get("name", "")),
            constraint_type=str(payload.get("constraint_type", "")).upper(),
            columns=tuple(str(value) for value in payload.get("columns") or ()),
            referenced_table=_optional_text(payload.get("referenced_table")),
            referenced_columns=tuple(
                str(value) for value in payload.get("referenced_columns") or ()
            ),
            expression=_optional_text(payload.get("expression")),
            enforced=_optional_bool(payload.get("enforced")),
            on_update=_optional_text(payload.get("on_update")),
            on_delete=_optional_text(payload.get("on_delete")),
            properties=dict(payload.get("properties") or {}),
        )


@dataclass(frozen=True)
class UCRelationshipMetadata:
    """A normalized relationship with evidence and authority metadata."""

    child_table: str
    child_columns: tuple[str, ...]
    parent_table: str
    parent_columns: tuple[str, ...]
    name: str | None = None
    source: str = "declared"
    confidence: float = 1.0
    evidence: tuple[str, ...] = ()
    on_update: str | None = None
    on_delete: str | None = None

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> UCRelationshipMetadata:
        return cls(
            child_table=str(payload["child_table"]),
            child_columns=tuple(str(value) for value in payload.get("child_columns") or ()),
            parent_table=str(payload["parent_table"]),
            parent_columns=tuple(str(value) for value in payload.get("parent_columns") or ()),
            name=_optional_text(payload.get("name")),
            source=str(payload.get("source", "declared")),
            confidence=float(payload.get("confidence", 1.0)),
            evidence=tuple(str(value) for value in payload.get("evidence") or ()),
            on_update=_optional_text(payload.get("on_update")),
            on_delete=_optional_text(payload.get("on_delete")),
        )


@dataclass(frozen=True)
class UCTableMetadata:
    """Metadata for one Unity Catalog table."""

    name: UnityCatalogTableName
    columns: tuple[UCColumnMetadata, ...]
    constraints: tuple[UCConstraintMetadata, ...] = ()
    relationships: tuple[UCRelationshipMetadata, ...] = ()
    table_type: str | None = None
    data_source_format: str | None = None
    description: str = ""
    tags: Mapping[str, str] = field(default_factory=dict)
    properties: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    unresolved_relationships: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> UCTableMetadata:
        raw_name = payload.get("name") or payload.get("qualified_name")
        if isinstance(raw_name, Mapping):
            name = UnityCatalogTableName(
                str(raw_name["catalog"]),
                str(raw_name["schema"]),
                str(raw_name["table"]),
            )
        else:
            name = UnityCatalogTableName.parse(str(raw_name))
        return cls(
            name=name,
            columns=tuple(UCColumnMetadata.from_dict(item) for item in payload.get("columns", ())),
            constraints=tuple(
                UCConstraintMetadata.from_dict(item) for item in payload.get("constraints", ())
            ),
            relationships=tuple(
                UCRelationshipMetadata.from_dict(item) for item in payload.get("relationships", ())
            ),
            table_type=_optional_text(payload.get("table_type")),
            data_source_format=_optional_text(payload.get("data_source_format")),
            description=str(payload.get("description", "") or ""),
            tags={str(key): str(value) for key, value in dict(payload.get("tags") or {}).items()},
            properties=dict(payload.get("properties") or {}),
            warnings=tuple(str(value) for value in payload.get("warnings") or ()),
            unresolved_relationships=tuple(
                str(value) for value in payload.get("unresolved_relationships") or ()
            ),
        )

    @property
    def qualified_name(self) -> str:
        return self.name.qualified_name

    @property
    def primary_key_columns(self) -> tuple[str, ...]:
        primary = next(
            (
                constraint
                for constraint in self.constraints
                if constraint.constraint_type == "PRIMARY KEY"
            ),
            None,
        )
        return primary.columns if primary is not None else ()

    @property
    def partition_columns(self) -> tuple[str, ...]:
        return tuple(
            column.name
            for column in sorted(
                (item for item in self.columns if item.partition_index is not None),
                key=lambda item: int(item.partition_index or 0),
            )
        )

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["name"] = {
            "catalog": self.name.catalog,
            "schema": self.name.schema,
            "table": self.name.table,
        }
        payload["qualified_name"] = self.qualified_name
        payload["primary_key_columns"] = list(self.primary_key_columns)
        payload["partition_columns"] = list(self.partition_columns)
        return _jsonable(payload)


@dataclass(frozen=True)
class UnityCatalogSnapshot:
    """A reusable metadata-only snapshot for a UC table graph."""

    root_table: str
    tables: Mapping[str, UCTableMetadata]
    relationships: tuple[UCRelationshipMetadata, ...] = ()
    warnings: tuple[str, ...] = ()
    captured_at: str = field(default_factory=utc_now_iso)
    source_platform: str = "databricks_unity_catalog"
    metadata_only_source_read: bool = True

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> UnityCatalogSnapshot:
        tables = {
            str(name): UCTableMetadata.from_dict(value)
            for name, value in dict(payload.get("tables") or {}).items()
        }
        return cls(
            root_table=str(payload["root_table"]),
            tables=tables,
            relationships=tuple(
                UCRelationshipMetadata.from_dict(item) for item in payload.get("relationships", ())
            ),
            warnings=tuple(str(value) for value in payload.get("warnings") or ()),
            captured_at=str(payload.get("captured_at") or utc_now_iso()),
            source_platform=str(payload.get("source_platform", "databricks_unity_catalog")),
            metadata_only_source_read=bool(payload.get("metadata_only_source_read", True)),
        )

    @classmethod
    def load(cls, path: str | Path) -> UnityCatalogSnapshot:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def as_dict(self) -> dict[str, Any]:
        payload = self._payload()
        payload["fingerprint"] = self.fingerprint()
        return payload

    def _payload(self) -> dict[str, Any]:
        return {
            "source_platform": self.source_platform,
            "metadata_only_source_read": self.metadata_only_source_read,
            "root_table": self.root_table,
            "captured_at": self.captured_at,
            "warnings": list(self.warnings),
            "relationships": [asdict(item) for item in self.relationships],
            "tables": {name: table.as_dict() for name, table in sorted(self.tables.items())},
        }

    def canonical_dict(self) -> dict[str, Any]:
        payload = self._payload()
        payload.pop("captured_at", None)
        return payload

    def fingerprint(self) -> str:
        raw = json.dumps(self.canonical_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def save(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(self.as_dict(), indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
        return destination

    def table(self, name: str | UnityCatalogTableName | None = None) -> UCTableMetadata:
        key = self.root_table if name is None else str(UnityCatalogTableName.parse(name))
        try:
            return self.tables[key]
        except KeyError as exc:
            raise KeyError(f"Table '{key}' is not present in this UC snapshot.") from exc


@dataclass(frozen=True)
class UCSchemaDiff:
    """Structured difference between two Unity Catalog metadata snapshots."""

    old_fingerprint: str
    new_fingerprint: str
    added_tables: tuple[str, ...] = ()
    removed_tables: tuple[str, ...] = ()
    added_columns: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    removed_columns: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    type_changes: Mapping[str, Mapping[str, tuple[str, str]]] = field(default_factory=dict)
    nullability_changes: Mapping[str, Mapping[str, tuple[bool, bool]]] = field(default_factory=dict)
    primary_key_changes: Mapping[str, tuple[tuple[str, ...], tuple[str, ...]]] = field(
        default_factory=dict
    )
    relationship_changes: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    @property
    def changed(self) -> bool:
        return any(
            (
                self.added_tables,
                self.removed_tables,
                self.added_columns,
                self.removed_columns,
                self.type_changes,
                self.nullability_changes,
                self.primary_key_changes,
                self.relationship_changes,
            )
        )

    def as_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self) | {"changed": self.changed})

    def to_text(self) -> str:
        if not self.changed:
            return "No Unity Catalog schema changes detected."
        lines = ["Unity Catalog schema changes detected:"]
        for name in self.added_tables:
            lines.append(f"- Added table: {name}")
        for name in self.removed_tables:
            lines.append(f"- Removed table: {name}")
        for table, columns in self.added_columns.items():
            lines.append(f"- {table}: added columns {', '.join(columns)}")
        for table, columns in self.removed_columns.items():
            lines.append(f"- {table}: removed columns {', '.join(columns)}")
        for table, columns in self.type_changes.items():
            for column, values in columns.items():
                lines.append(f"- {table}.{column}: type {values[0]} -> {values[1]}")
        for table, columns in self.nullability_changes.items():
            for column, values in columns.items():
                lines.append(f"- {table}.{column}: nullable {values[0]} -> {values[1]}")
        for table, values in self.primary_key_changes.items():
            lines.append(f"- {table}: primary key {values[0]} -> {values[1]}")
        for change, values in self.relationship_changes.items():
            lines.append(f"- {change} relationships: {', '.join(values)}")
        return "\n".join(lines)


def quote_identifier(value: str) -> str:
    """Quote a Databricks SQL identifier without allowing delimiter escape."""

    text = str(value)
    if not text or "\x00" in text:
        raise ValueError("SQL identifiers cannot be empty or contain NUL characters.")
    return f"`{text.replace('`', '``')}`"


def quote_literal(value: str) -> str:
    """Return a SQL string literal for metadata predicates."""

    text = str(value)
    if "\x00" in text:
        raise ValueError("SQL literals cannot contain NUL characters.")
    return "'" + text.replace("'", "''") + "'"


def table_metadata_to_schema(table: UCTableMetadata) -> TableSchema:
    """Convert UC metadata into Great Generator's existing table contract."""

    primary_columns = table.primary_key_columns
    unique_constraints = tuple(
        UniqueConstraint(columns=item.columns, name=item.name)
        for item in table.constraints
        if item.constraint_type in {"UNIQUE", "PRIMARY KEY"}
    )
    checks = tuple(
        CheckConstraint(expression=item.expression or "", name=item.name, columns=item.columns)
        for item in table.constraints
        if item.constraint_type == "CHECK" and item.expression
    )
    foreign_keys: list[ForeignKey] = []
    for relationship in table.relationships:
        parent = UnityCatalogTableName.parse(relationship.parent_table)
        for child_column, parent_column in zip(
            relationship.child_columns, relationship.parent_columns
        ):
            column = next((item for item in table.columns if item.name == child_column), None)
            foreign_keys.append(
                ForeignKey(
                    column=child_column,
                    parent_table=parent.table,
                    parent_column=parent_column,
                    constraint_name=relationship.name,
                    child_table=table.name.table,
                    child_columns=relationship.child_columns,
                    parent_columns=relationship.parent_columns,
                    nullable=column.nullable if column is not None else None,
                    on_update=relationship.on_update,
                    on_delete=relationship.on_delete,
                    metadata={
                        "source": relationship.source,
                        "confidence": relationship.confidence,
                        "qualified_parent_table": relationship.parent_table,
                    },
                )
            )
    return TableSchema(
        name=table.name.table,
        namespace=f"{table.name.catalog}.{table.name.schema}",
        columns=tuple(_column_to_spec(column) for column in table.columns),
        primary_key=primary_columns[0] if primary_columns else None,
        primary_key_columns=primary_columns,
        foreign_keys=tuple(foreign_keys),
        unique_constraints=unique_constraints,
        checks=checks,
        description=table.description,
        tags=tuple(f"{key}:{value}" for key, value in sorted(table.tags.items())),
        metadata={
            "source": "databricks_unity_catalog",
            "qualified_name": table.qualified_name,
            "table_type": table.table_type,
            "data_source_format": table.data_source_format,
            "partition_columns": table.partition_columns,
            "properties": dict(table.properties),
            "warnings": table.warnings,
        },
    )


def _column_to_spec(column: UCColumnMetadata) -> ColumnSpec:
    dtype = normalize_databricks_type(column.data_type, column.full_data_type)
    semantic_tags = tuple(f"{key}:{value}" for key, value in sorted(column.tags.items()))
    return ColumnSpec(
        name=column.name,
        dtype=dtype,
        nullable=column.nullable,
        description=column.description,
        original_type=column.full_data_type or column.data_type,
        default_expression=column.default_expression,
        precision=column.precision,
        scale=column.scale,
        max_length=column.max_length,
        tags=semantic_tags,
        metadata={
            "generated_expression": column.generated_expression,
            "identity": column.identity,
            "partition_index": column.partition_index,
            "properties": dict(column.properties),
        },
    )


def normalize_databricks_type(data_type: str, full_data_type: str | None = None) -> str:
    """Normalize supported Databricks scalar types for existing generators."""

    raw = (full_data_type or data_type).strip().lower()
    scalar = raw.split("(", 1)[0].strip()
    aliases = {
        "byte": "tinyint",
        "tinyint": "tinyint",
        "short": "smallint",
        "smallint": "smallint",
        "int": "int",
        "long": "bigint",
        "bigint": "bigint",
        "integer": "int",
        "float": "float",
        "double": "double",
        "decimal": raw if raw.startswith("decimal") else "decimal(18,2)",
        "numeric": raw if raw.startswith("numeric") else "decimal(18,2)",
        "char": raw,
        "varchar": raw,
        "string": "string",
        "binary": "binary",
        "boolean": "boolean",
        "date": "date",
        "timestamp": "timestamp",
        "timestamp_ntz": "timestamp",
        "interval": "string",
    }
    if scalar in {"array", "map", "struct", "variant"} or raw.startswith(
        ("array<", "map<", "struct<", "variant<")
    ):
        raise ValueError(
            f"Unity Catalog type '{raw}' is preserved in metadata but row generation for "
            "complex Databricks types is not supported in this release."
        )
    if scalar not in aliases:
        raise ValueError(f"Unsupported Databricks SQL type '{raw}'.")
    return aliases[scalar]


def _split_qualified_identifier(value: str) -> list[str]:
    text = value.strip()
    if not text:
        return []
    parts: list[str] = []
    current: list[str] = []
    quoted = False
    index = 0
    while index < len(text):
        char = text[index]
        if char == "`":
            if quoted and index + 1 < len(text) and text[index + 1] == "`":
                current.append("`")
                index += 2
                continue
            quoted = not quoted
        elif char == "." and not quoted:
            part = "".join(current).strip()
            if not part:
                raise ValueError("Unity Catalog identifiers cannot contain empty parts.")
            parts.append(part)
            current = []
        else:
            current.append(char)
        index += 1
    if quoted:
        raise ValueError("Unity Catalog identifier contains an unclosed backtick.")
    part = "".join(current).strip()
    if not part:
        raise ValueError("Unity Catalog identifiers cannot contain empty parts.")
    parts.append(part)
    return parts


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "yes", "1"}


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value
