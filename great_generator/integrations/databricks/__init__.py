"""Optional Databricks Unity Catalog integration."""

from .generation import (
    build_uc_generation_manifest,
    compare_uc_schema_snapshots,
    generate_from_unity_catalog,
    generate_relational_from_unity_catalog,
    generate_uc_cdc,
    inspect_unity_catalog_table,
)
from .models import (
    UCColumnMetadata,
    UCConstraintMetadata,
    UCRelationshipMetadata,
    UCSchemaDiff,
    UCTableMetadata,
    UnityCatalogSnapshot,
    UnityCatalogTableName,
)
from .notebook_builder import generate_uc_ingestion_code
from .uc_client import (
    DatabricksSDKQueryClient,
    SparkUnityCatalogQueryClient,
    StaticUnityCatalogClient,
    UnityCatalogAccessError,
    UnityCatalogTableNotFoundError,
)
from .validation import validate_uc_relational_data

__all__ = [
    "DatabricksSDKQueryClient",
    "SparkUnityCatalogQueryClient",
    "StaticUnityCatalogClient",
    "UCColumnMetadata",
    "UCConstraintMetadata",
    "UCRelationshipMetadata",
    "UCSchemaDiff",
    "UCTableMetadata",
    "UnityCatalogAccessError",
    "UnityCatalogSnapshot",
    "UnityCatalogTableName",
    "UnityCatalogTableNotFoundError",
    "build_uc_generation_manifest",
    "compare_uc_schema_snapshots",
    "generate_from_unity_catalog",
    "generate_relational_from_unity_catalog",
    "generate_uc_cdc",
    "generate_uc_ingestion_code",
    "inspect_unity_catalog_table",
    "validate_uc_relational_data",
]
