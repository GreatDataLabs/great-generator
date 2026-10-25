"""Unity Catalog metadata clients with lazy Databricks dependencies."""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

from .models import UCTableMetadata, UnityCatalogSnapshot, UnityCatalogTableName


class MetadataQueryClient(Protocol):
    """Small protocol used by the metadata reader."""

    def query(self, statement: str) -> list[dict[str, Any]]:
        """Execute a metadata-only SQL statement and return mapping rows."""


class SparkUnityCatalogQueryClient:
    """Read information-schema metadata through an existing SparkSession."""

    def __init__(self, spark: Any) -> None:
        if spark is None or not hasattr(spark, "sql"):
            raise ValueError("A SparkSession with a sql(...) method is required.")
        self.spark = spark

    def query(self, statement: str) -> list[dict[str, Any]]:
        try:
            rows = self.spark.sql(statement).collect()
        except Exception as exc:  # noqa: BLE001 - normalize provider-specific errors
            raise UnityCatalogAccessError(_safe_error_message(exc)) from exc
        return [
            dict(row.asDict(recursive=True)) if hasattr(row, "asDict") else dict(row)
            for row in rows
        ]


class DatabricksSDKQueryClient:
    """Read UC metadata with Databricks unified authentication and SQL execution."""

    def __init__(
        self,
        *,
        warehouse_id: str,
        workspace_client: Any | None = None,
        poll_interval_seconds: float = 0.2,
        timeout_seconds: float = 30.0,
    ) -> None:
        if not warehouse_id or not str(warehouse_id).strip():
            raise ValueError("warehouse_id is required for SDK metadata queries.")
        if workspace_client is None:
            try:
                from databricks.sdk import WorkspaceClient
            except ImportError as exc:
                raise ImportError(
                    "Databricks Unity Catalog SDK access requires: "
                    'pip install "great-generator[databricks]"'
                ) from exc
            workspace_client = WorkspaceClient()
        self.workspace_client = workspace_client
        self.warehouse_id = str(warehouse_id)
        self.poll_interval_seconds = float(poll_interval_seconds)
        self.timeout_seconds = float(timeout_seconds)

    def query(self, statement: str) -> list[dict[str, Any]]:
        service = getattr(self.workspace_client, "statement_execution", None)
        if service is None:
            raise UnityCatalogAccessError(
                "The configured Databricks SDK client does not expose statement_execution."
            )
        try:
            response = service.execute_statement(
                statement=statement,
                warehouse_id=self.warehouse_id,
                wait_timeout="30s",
            )
            response = self._wait_for_result(service, response)
            return _statement_rows(response)
        except UnityCatalogAccessError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalize provider-specific errors
            raise UnityCatalogAccessError(_safe_error_message(exc)) from exc

    def _wait_for_result(self, service: Any, response: Any) -> Any:
        statement_id = getattr(response, "statement_id", None)
        deadline = time.monotonic() + self.timeout_seconds
        while _statement_state(response) in {"PENDING", "RUNNING"}:
            if not statement_id:
                raise UnityCatalogAccessError(
                    "Databricks returned a pending statement without a statement_id."
                )
            if time.monotonic() >= deadline:
                raise UnityCatalogAccessError(
                    f"Unity Catalog metadata query timed out after {self.timeout_seconds:g}s."
                )
            time.sleep(self.poll_interval_seconds)
            response = service.get_statement(statement_id=statement_id)
        state = _statement_state(response)
        if state and state not in {"SUCCEEDED", "CLOSED"}:
            error = getattr(getattr(response, "status", None), "error", None)
            message = getattr(error, "message", None) or f"statement ended in state {state}"
            raise UnityCatalogAccessError(str(message))
        return response


class StaticUnityCatalogClient:
    """Offline metadata client for tests, examples, and reviewed snapshots."""

    def __init__(self, snapshot: UnityCatalogSnapshot | Mapping[str, Any]) -> None:
        self.snapshot = (
            snapshot
            if isinstance(snapshot, UnityCatalogSnapshot)
            else UnityCatalogSnapshot.from_dict(snapshot)
        )

    @classmethod
    def from_path(cls, path: str | Path) -> StaticUnityCatalogClient:
        return cls(UnityCatalogSnapshot.load(path))

    def get_table_metadata(self, table: str | UnityCatalogTableName, **_: Any) -> UCTableMetadata:
        name = UnityCatalogTableName.parse(table).qualified_name
        try:
            return self.snapshot.tables[name]
        except KeyError as exc:
            raise UnityCatalogTableNotFoundError(
                f"Unity Catalog table '{name}' is not present in the static metadata fixture."
            ) from exc

    def find_related_tables(
        self,
        table: str | UnityCatalogTableName,
        *,
        direction: str = "parents",
    ) -> list[UnityCatalogTableName]:
        name = UnityCatalogTableName.parse(table).qualified_name
        related: set[str] = set()
        for relationship in self.snapshot.relationships:
            if direction in {"parents", "both"} and relationship.child_table == name:
                related.add(relationship.parent_table)
            if direction in {"children", "both"} and relationship.parent_table == name:
                related.add(relationship.child_table)
        return [UnityCatalogTableName.parse(value) for value in sorted(related)]


class UnityCatalogAccessError(RuntimeError):
    """Raised when UC metadata cannot be read with current permissions/configuration."""


class UnityCatalogTableNotFoundError(UnityCatalogAccessError):
    """Raised when the requested table is not visible through information_schema."""


def resolve_query_client(
    *,
    spark: Any | None = None,
    warehouse_id: str | None = None,
    workspace_client: Any | None = None,
) -> MetadataQueryClient:
    """Resolve notebook Spark or SDK unified-auth metadata access."""

    if spark is not None:
        return SparkUnityCatalogQueryClient(spark)
    if warehouse_id:
        return DatabricksSDKQueryClient(
            warehouse_id=warehouse_id,
            workspace_client=workspace_client,
        )
    raise ValueError(
        "Unity Catalog inspection requires either spark=<SparkSession>, an explicit "
        "metadata client, or warehouse_id=<SQL warehouse id> for Databricks SDK access."
    )


def _statement_state(response: Any) -> str:
    state = getattr(getattr(response, "status", None), "state", None)
    value = getattr(state, "value", state)
    return str(value or "").upper()


def _statement_rows(response: Any) -> list[dict[str, Any]]:
    manifest = getattr(response, "manifest", None)
    schema = getattr(manifest, "schema", None)
    columns = getattr(schema, "columns", None) or ()
    column_names = [str(getattr(column, "name", "")) for column in columns]
    result = getattr(response, "result", None)
    raw_rows: Sequence[Any] = getattr(result, "data_array", None) or ()
    if not column_names and raw_rows:
        raise UnityCatalogAccessError(
            "Databricks statement response did not include result column metadata."
        )
    return [dict(zip(column_names, row)) for row in raw_rows]


def _safe_error_message(exc: Exception) -> str:
    """Return provider diagnostics without serializing credentials or client config."""

    message = str(exc).strip() or exc.__class__.__name__
    lowered = message.lower()
    for marker in ("token=", "authorization:", "password="):
        if marker in lowered:
            return (
                "Unity Catalog metadata access failed. The provider error may contain a "
                "credential and was intentionally redacted."
            )
    return f"Unity Catalog metadata access failed: {message}"
