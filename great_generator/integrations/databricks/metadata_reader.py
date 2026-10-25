"""Read permitted Unity Catalog metadata without reading table records."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from typing import Any

from .models import (
    UCColumnMetadata,
    UCConstraintMetadata,
    UCRelationshipMetadata,
    UCTableMetadata,
    UnityCatalogTableName,
    quote_identifier,
    quote_literal,
)
from .uc_client import (
    MetadataQueryClient,
    UnityCatalogAccessError,
    UnityCatalogTableNotFoundError,
)


class UnityCatalogMetadataReader:
    """Information-schema adapter for one Databricks catalog at a time."""

    def __init__(self, query_client: MetadataQueryClient) -> None:
        self.query_client = query_client

    def get_table_metadata(
        self,
        table: str | UnityCatalogTableName,
        *,
        include_constraints: bool = True,
        include_tags: bool = True,
        include_relationships: bool = True,
    ) -> UCTableMetadata:
        name = UnityCatalogTableName.parse(table)
        table_rows = self._query(_table_query(name))
        if not table_rows:
            raise UnityCatalogTableNotFoundError(
                f"Unity Catalog table '{name}' was not found or is not visible to the caller."
            )
        table_row = _normalized_row(table_rows[0])
        column_rows = self._query(_columns_query(name))
        if not column_rows:
            raise UnityCatalogAccessError(
                f"No visible column metadata was returned for Unity Catalog table '{name}'."
            )

        warnings: list[str] = [
            "Unity Catalog constraints are informational metadata; Great Generator validates "
            "the generated synthetic output separately.",
            "Generated-column expressions, identity settings, and arbitrary table properties "
            "are preserved only when exposed by the configured metadata source.",
        ]
        column_tags: dict[str, dict[str, str]] = defaultdict(dict)
        table_tags: dict[str, str] = {}
        if include_tags:
            warnings.append(
                "Visible tag names and values are copied into the metadata snapshot as plain "
                "text; keep sensitive information out of Unity Catalog tags."
            )
            try:
                for row in self._query(_column_tags_query(name)):
                    item = _normalized_row(row)
                    column_tags[str(item.get("column_name", ""))][str(item.get("tag_name", ""))] = (
                        str(item.get("tag_value", ""))
                    )
                for row in self._query(_table_tags_query(name)):
                    item = _normalized_row(row)
                    table_tags[str(item.get("tag_name", ""))] = str(item.get("tag_value", ""))
            except UnityCatalogAccessError as exc:
                warnings.append(
                    "Tags were not available with the current runtime or permissions: " f"{exc}"
                )

        constraints: tuple[UCConstraintMetadata, ...] = ()
        relationships: tuple[UCRelationshipMetadata, ...] = ()
        unresolved: list[str] = []
        if include_constraints:
            constraints = self._read_constraints(name)
        if include_relationships:
            try:
                relationships = self._read_relationships(name, role="child")
            except UnityCatalogAccessError as exc:
                warnings.append(f"Foreign-key metadata was not available: {exc}")
                unresolved.append(str(exc))

        columns = tuple(
            _column_from_row(row, tags=column_tags.get(str(_get(row, "COLUMN_NAME")), {}))
            for row in sorted(
                column_rows, key=lambda item: int(_get(item, "ORDINAL_POSITION") or 0)
            )
        )
        return UCTableMetadata(
            name=name,
            columns=columns,
            constraints=constraints,
            relationships=relationships,
            table_type=_optional_text(table_row.get("table_type")),
            data_source_format=_optional_text(table_row.get("data_source_format")),
            description=str(table_row.get("comment", "") or ""),
            tags=table_tags,
            properties={
                key: value
                for key, value in table_row.items()
                if key
                not in {
                    "table_catalog",
                    "table_schema",
                    "table_name",
                    "table_type",
                    "data_source_format",
                    "comment",
                }
                and value is not None
            },
            warnings=tuple(warnings),
            unresolved_relationships=tuple(unresolved),
        )

    def find_related_tables(
        self,
        table: str | UnityCatalogTableName,
        *,
        direction: str = "parents",
    ) -> list[UnityCatalogTableName]:
        name = UnityCatalogTableName.parse(table)
        if direction not in {"parents", "children", "both"}:
            raise ValueError("related_direction must be 'parents', 'children', or 'both'.")
        relationships: list[UCRelationshipMetadata] = []
        if direction in {"parents", "both"}:
            relationships.extend(self._read_relationships(name, role="child"))
        if direction in {"children", "both"}:
            relationships.extend(self._read_relationships(name, role="parent"))
        names: set[str] = set()
        for relationship in relationships:
            if relationship.child_table == name.qualified_name:
                names.add(relationship.parent_table)
            elif relationship.parent_table == name.qualified_name:
                names.add(relationship.child_table)
        return [UnityCatalogTableName.parse(value) for value in sorted(names)]

    def _read_constraints(self, name: UnityCatalogTableName) -> tuple[UCConstraintMetadata, ...]:
        rows = self._query(_constraints_query(name))
        grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
        for raw in rows:
            row = _normalized_row(raw)
            grouped[
                (str(row.get("constraint_name", "")), str(row.get("constraint_type", "")))
            ].append(row)
        constraints: list[UCConstraintMetadata] = []
        for (constraint_name, constraint_type), items in sorted(grouped.items()):
            ordered = sorted(items, key=lambda item: int(item.get("ordinal_position") or 0))
            columns = tuple(
                str(item["column_name"])
                for item in ordered
                if item.get("column_name") not in (None, "")
            )
            constraints.append(
                UCConstraintMetadata(
                    name=constraint_name,
                    constraint_type=constraint_type.upper(),
                    columns=columns,
                    enforced=_yes_no(ordered[0].get("enforced")) if ordered else None,
                    properties={
                        "is_deferrable": ordered[0].get("is_deferrable") if ordered else None,
                        "initially_deferred": (
                            ordered[0].get("initially_deferred") if ordered else None
                        ),
                    },
                )
            )
        return tuple(constraints)

    def _read_relationships(
        self,
        name: UnityCatalogTableName,
        *,
        role: str,
    ) -> tuple[UCRelationshipMetadata, ...]:
        rows = self._query(_relationships_query(name, role=role))
        grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for raw in rows:
            row = _normalized_row(raw)
            grouped[str(row.get("constraint_name", ""))].append(row)
        relationships: list[UCRelationshipMetadata] = []
        for constraint_name, items in sorted(grouped.items()):
            ordered = sorted(items, key=lambda item: int(item.get("child_ordinal") or 0))
            first = ordered[0]
            child_table = ".".join(
                str(first[key]) for key in ("child_catalog", "child_schema", "child_table")
            )
            parent_table = ".".join(
                str(first[key]) for key in ("parent_catalog", "parent_schema", "parent_table")
            )
            relationships.append(
                UCRelationshipMetadata(
                    name=constraint_name or None,
                    child_table=child_table,
                    child_columns=tuple(str(item["child_column"]) for item in ordered),
                    parent_table=parent_table,
                    parent_columns=tuple(str(item["parent_column"]) for item in ordered),
                    source="declared",
                    confidence=1.0,
                    evidence=("Unity Catalog INFORMATION_SCHEMA foreign-key constraint",),
                    on_update=_optional_text(first.get("update_rule")),
                    on_delete=_optional_text(first.get("delete_rule")),
                )
            )
        return tuple(relationships)

    def _query(self, statement: str) -> list[dict[str, Any]]:
        return self.query_client.query(statement)


def _table_query(name: UnityCatalogTableName) -> str:
    return f"""
SELECT TABLE_CATALOG, TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE, IS_INSERTABLE_INTO,
       DATA_SOURCE_FORMAT, STORAGE_PATH, COMMENT
FROM {quote_identifier(name.catalog)}.information_schema.tables
WHERE TABLE_CATALOG = {quote_literal(name.catalog)}
  AND TABLE_SCHEMA = {quote_literal(name.schema)}
  AND TABLE_NAME = {quote_literal(name.table)}
""".strip()


def _columns_query(name: UnityCatalogTableName) -> str:
    return f"""
SELECT TABLE_CATALOG, TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, ORDINAL_POSITION,
       COLUMN_DEFAULT, IS_NULLABLE, DATA_TYPE, FULL_DATA_TYPE,
       CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE,
       IS_IDENTITY, IS_GENERATED, GENERATION_EXPRESSION, COMMENT, PARTITION_INDEX
FROM {quote_identifier(name.catalog)}.information_schema.columns
WHERE TABLE_CATALOG = {quote_literal(name.catalog)}
  AND TABLE_SCHEMA = {quote_literal(name.schema)}
  AND TABLE_NAME = {quote_literal(name.table)}
ORDER BY ORDINAL_POSITION
""".strip()


def _constraints_query(name: UnityCatalogTableName) -> str:
    catalog = quote_identifier(name.catalog)
    return f"""
SELECT tc.CONSTRAINT_NAME, tc.CONSTRAINT_TYPE, tc.IS_DEFERRABLE,
       tc.INITIALLY_DEFERRED, tc.ENFORCED,
       kcu.COLUMN_NAME, kcu.ORDINAL_POSITION
FROM {catalog}.information_schema.table_constraints tc
LEFT JOIN {catalog}.information_schema.key_column_usage kcu
  ON tc.CONSTRAINT_CATALOG = kcu.CONSTRAINT_CATALOG
 AND tc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
 AND tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
WHERE tc.TABLE_CATALOG = {quote_literal(name.catalog)}
  AND tc.TABLE_SCHEMA = {quote_literal(name.schema)}
  AND tc.TABLE_NAME = {quote_literal(name.table)}
ORDER BY tc.CONSTRAINT_NAME, kcu.ORDINAL_POSITION
""".strip()


def _relationships_query(name: UnityCatalogTableName, *, role: str) -> str:
    if role not in {"child", "parent"}:
        raise ValueError("relationship role must be 'child' or 'parent'.")
    catalog = quote_identifier(name.catalog)
    child_filter = f"""
child.TABLE_CATALOG = {quote_literal(name.catalog)}
  AND child.TABLE_SCHEMA = {quote_literal(name.schema)}
  AND child.TABLE_NAME = {quote_literal(name.table)}
""".strip()
    parent_filter = f"""
parent.TABLE_CATALOG = {quote_literal(name.catalog)}
  AND parent.TABLE_SCHEMA = {quote_literal(name.schema)}
  AND parent.TABLE_NAME = {quote_literal(name.table)}
""".strip()
    predicate = child_filter if role == "child" else parent_filter
    return f"""
SELECT rc.CONSTRAINT_NAME,
       child.TABLE_CATALOG AS CHILD_CATALOG,
       child.TABLE_SCHEMA AS CHILD_SCHEMA,
       child.TABLE_NAME AS CHILD_TABLE,
       child.COLUMN_NAME AS CHILD_COLUMN,
       child.ORDINAL_POSITION AS CHILD_ORDINAL,
       parent.TABLE_CATALOG AS PARENT_CATALOG,
       parent.TABLE_SCHEMA AS PARENT_SCHEMA,
       parent.TABLE_NAME AS PARENT_TABLE,
       parent.COLUMN_NAME AS PARENT_COLUMN,
       rc.UPDATE_RULE, rc.DELETE_RULE
FROM {catalog}.information_schema.referential_constraints rc
JOIN {catalog}.information_schema.key_column_usage child
  ON rc.CONSTRAINT_CATALOG = child.CONSTRAINT_CATALOG
 AND rc.CONSTRAINT_SCHEMA = child.CONSTRAINT_SCHEMA
 AND rc.CONSTRAINT_NAME = child.CONSTRAINT_NAME
JOIN {catalog}.information_schema.key_column_usage parent
  ON rc.UNIQUE_CONSTRAINT_CATALOG = parent.CONSTRAINT_CATALOG
 AND rc.UNIQUE_CONSTRAINT_SCHEMA = parent.CONSTRAINT_SCHEMA
 AND rc.UNIQUE_CONSTRAINT_NAME = parent.CONSTRAINT_NAME
 AND child.POSITION_IN_UNIQUE_CONSTRAINT = parent.ORDINAL_POSITION
WHERE {predicate}
ORDER BY rc.CONSTRAINT_NAME, child.ORDINAL_POSITION
""".strip()


def _column_tags_query(name: UnityCatalogTableName) -> str:
    return f"""
SELECT COLUMN_NAME, TAG_NAME, TAG_VALUE
FROM {quote_identifier(name.catalog)}.information_schema.column_tags
WHERE CATALOG_NAME = {quote_literal(name.catalog)}
  AND SCHEMA_NAME = {quote_literal(name.schema)}
  AND TABLE_NAME = {quote_literal(name.table)}
""".strip()


def _table_tags_query(name: UnityCatalogTableName) -> str:
    return f"""
SELECT TAG_NAME, TAG_VALUE
FROM {quote_identifier(name.catalog)}.information_schema.table_tags
WHERE CATALOG_NAME = {quote_literal(name.catalog)}
  AND SCHEMA_NAME = {quote_literal(name.schema)}
  AND TABLE_NAME = {quote_literal(name.table)}
""".strip()


def _column_from_row(row: Mapping[str, Any], *, tags: Mapping[str, str]) -> UCColumnMetadata:
    item = _normalized_row(row)
    return UCColumnMetadata(
        name=str(item["column_name"]),
        position=int(item.get("ordinal_position") or 0),
        data_type=str(item.get("data_type") or "string"),
        full_data_type=_optional_text(item.get("full_data_type")),
        nullable=str(item.get("is_nullable", "YES")).upper() == "YES",
        description=str(item.get("comment", "") or ""),
        default_expression=_optional_text(item.get("column_default")),
        generated_expression=_optional_text(item.get("generation_expression")),
        identity=str(item.get("is_identity", "NO")).upper() == "YES",
        partition_index=_optional_int(item.get("partition_index")),
        precision=_optional_int(item.get("numeric_precision")),
        scale=_optional_int(item.get("numeric_scale")),
        max_length=_optional_int(item.get("character_maximum_length")),
        tags=dict(tags),
    )


def _get(row: Mapping[str, Any], key: str) -> Any:
    return _normalized_row(row).get(key.lower())


def _normalized_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key).lower(): value for key, value in row.items()}


def _yes_no(value: Any) -> bool | None:
    if value is None:
        return None
    return str(value).upper() in {"YES", "TRUE", "1"}


def _optional_text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)
