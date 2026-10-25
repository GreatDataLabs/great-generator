import builtins
import json
from pathlib import Path

import pandas as pd
import pytest

from great_generator import (
    StaticUnityCatalogClient,
    UnityCatalogSnapshot,
    UnityCatalogTableName,
    compare_uc_schema_snapshots,
    generate_from_unity_catalog,
    generate_relational_from_unity_catalog,
    generate_uc_cdc,
    generate_uc_ingestion_code,
    inspect_unity_catalog_table,
)
from great_generator.integrations.databricks.metadata_reader import UnityCatalogMetadataReader
from great_generator.integrations.databricks.models import (
    normalize_databricks_type,
    quote_identifier,
)
from great_generator.integrations.databricks.uc_client import (
    DatabricksSDKQueryClient,
    UnityCatalogAccessError,
    UnityCatalogTableNotFoundError,
)

FIXTURE = Path("tests/fixtures/unity_catalog/retail_sales.json")


@pytest.fixture
def uc_client():
    return StaticUnityCatalogClient.from_path(FIXTURE)


def test_three_part_table_name_parsing_and_safe_quoting():
    name = UnityCatalogTableName.parse("`retail`.`sales`.`fact.orders`")

    assert name.parts == ("retail", "sales", "fact.orders")
    assert name.quoted_name == "`retail`.`sales`.`fact.orders`"
    assert quote_identifier("a`b") == "`a``b`"
    with pytest.raises(ValueError, match="three-part"):
        UnityCatalogTableName.parse("sales.orders")


def test_inspect_uc_table_discovers_declared_parent_graph(uc_client):
    snapshot = inspect_unity_catalog_table(
        "retail.sales.fact_orders",
        include_related=True,
        related_direction="parents",
        client=uc_client,
    )

    assert set(snapshot.tables) == {
        "retail.sales.dim_customer",
        "retail.sales.dim_product",
        "retail.sales.fact_orders",
    }
    assert len(snapshot.relationships) == 2
    assert snapshot.table().primary_key_columns == ("order_id",)
    assert snapshot.table().partition_columns == ("order_date",)
    assert snapshot.metadata_only_source_read is True


def test_uc_snapshot_round_trip_and_stable_fingerprint(tmp_path, uc_client):
    snapshot = inspect_unity_catalog_table(
        "retail.sales.fact_orders", include_related=True, client=uc_client
    )
    path = snapshot.save(tmp_path / "snapshot.json")
    loaded = UnityCatalogSnapshot.load(path)

    assert loaded.fingerprint() == snapshot.fingerprint()
    assert loaded.root_table == snapshot.root_table


def test_single_uc_generation_is_deterministic_and_query_aware(uc_client):
    kwargs = {
        "table": "retail.sales.dim_customer",
        "rows": 25,
        "seed": 42,
        "client": uc_client,
        "required_values": {"region": ["EAST", "WEST"]},
    }

    first = generate_from_unity_catalog(**kwargs)
    second = generate_from_unity_catalog(**kwargs)

    pd.testing.assert_frame_equal(first, second)
    assert isinstance(first, pd.DataFrame)
    assert {"EAST", "WEST"}.issubset(set(first["region"]))
    assert first["customer_id"].is_unique


def test_single_uc_generation_qualifies_embedded_query_profile(uc_client):
    data = generate_from_unity_catalog(
        "retail.sales.dim_customer",
        rows=24,
        seed=42,
        client=uc_client,
        query_profile={
            "required_values": {"region": ["EAST", "WEST"]},
            "partition_by": {
                "column": "region",
                "values": ["EAST", "WEST"],
                "distribution": "balanced",
            },
        },
    )

    assert {"EAST", "WEST"}.issubset(set(data["region"]))
    assert abs(int((data["region"] == "EAST").sum()) - 12) <= 1


def test_relational_uc_generation_preserves_simple_and_composite_foreign_keys(uc_client):
    data, report = generate_relational_from_unity_catalog(
        "retail.sales.fact_orders",
        include_related=True,
        rows={"dim_customer": 12, "dim_product": 8, "fact_orders": 60},
        seed=17,
        client=uc_client,
        return_report=True,
    )

    assert set(data) == {"dim_customer", "dim_product", "fact_orders"}
    assert data["fact_orders"]["customer_id"].isin(data["dim_customer"]["customer_id"]).all()
    child_keys = data["fact_orders"][["product_id", "product_version"]]
    parent_keys = data["dim_product"][["product_id", "product_version"]]
    joined = child_keys.merge(parent_keys.drop_duplicates(), how="left", indicator=True)
    assert (joined["_merge"] == "both").all()
    assert report["validation"]["passed"] is True
    assert report["manifest"]["synthetic"] is True


def test_explicit_relationships_work_when_constraint_graph_is_not_selected(uc_client):
    data = generate_relational_from_unity_catalog(
        "retail.sales.fact_orders",
        include_related=False,
        relationship_strategy="explicit",
        relationships={
            "fact_orders.customer_id": "dim_customer.customer_id",
        },
        rows={"fact_orders": 20, "dim_customer": 5},
        seed=7,
        client=uc_client,
    )

    assert set(data) == {"dim_customer", "fact_orders"}
    assert data["fact_orders"]["customer_id"].isin(data["dim_customer"]["customer_id"]).all()


def test_anomaly_aliases_are_explicit_and_reported(uc_client):
    data, report = generate_relational_from_unity_catalog(
        "retail.sales.fact_orders",
        include_related=True,
        rows={"dim_customer": 10, "dim_product": 5, "fact_orders": 40},
        anomalies={"duplicate_records": 0.1},
        seed=3,
        client=uc_client,
        return_report=True,
    )

    assert len(data["fact_orders"]) > 40
    assert report["validation"]["expected_anomalies"] == {"duplicate_rate": 0.1}


def test_inferred_relationships_are_labeled_with_confidence(uc_client):
    _data, report = generate_relational_from_unity_catalog(
        "retail.sales.fact_orders",
        include_related=False,
        relationship_strategy="inferred",
        # These references bound the inspected graph; inference still decides the relationship.
        relationships={"fact_orders.customer_id": "dim_customer.customer_id"},
        rows={"fact_orders": 20, "dim_customer": 5},
        seed=9,
        client=uc_client,
        return_report=True,
    )

    inferred = [item for item in report["relationships"] if item["source"] == "inferred"]
    assert len(inferred) == 1
    assert inferred[0]["confidence"] == 0.75
    assert inferred[0]["evidence"]


def test_uc_scd2_requires_explicit_config_and_validates_history(uc_client):
    data = generate_relational_from_unity_catalog(
        "retail.sales.dim_customer",
        include_related=False,
        model_type="scd2",
        scd2_config={
            "natural_key": ["customer_id"],
            "surrogate_key": "customer_sk",
            "effective_start": "effective_start_date",
            "effective_end": "effective_end_date",
            "current_flag": "is_current",
        },
        rows=20,
        seed=4,
        client=uc_client,
    )

    history = data["dim_customer_history"]
    assert history["customer_sk"].is_unique
    assert history.groupby("customer_id")["is_current"].sum().eq(1).all()
    assert (history["effective_start_date"] < history["effective_end_date"]).all()


def test_uc_cdc_is_deterministic_and_contains_portable_change_metadata(uc_client):
    first = generate_uc_cdc(
        "retail.sales.fact_orders",
        rows=30,
        operations={"INSERT": 0.5, "UPDATE": 0.3, "DELETE": 0.2},
        seed=11,
        client=uc_client,
    )
    second = generate_uc_cdc(
        "retail.sales.fact_orders",
        rows=30,
        operations={"INSERT": 0.5, "UPDATE": 0.3, "DELETE": 0.2},
        seed=11,
        client=uc_client,
    )

    pd.testing.assert_frame_equal(first, second)
    assert set(first["operation"]).issubset({"INSERT", "UPDATE", "DELETE"})
    assert first["sequence_number"].tolist() == list(range(1, 31))
    assert first["synthetic"].all()
    assert {"before", "after", "event_timestamp", "primary_key"}.issubset(first.columns)


def test_compare_uc_snapshots_detects_column_and_type_changes(uc_client):
    old = inspect_unity_catalog_table(
        "retail.sales.fact_orders", include_related=True, client=uc_client
    )
    payload = old.as_dict()
    columns = payload["tables"]["retail.sales.fact_orders"]["columns"]
    columns[0]["data_type"] = "STRING"
    columns.append(
        {
            "name": "channel",
            "position": 8,
            "data_type": "STRING",
            "nullable": True,
        }
    )
    new = UnityCatalogSnapshot.from_dict(payload)

    diff = compare_uc_schema_snapshots(old, new)

    assert diff.changed is True
    assert diff.added_columns["retail.sales.fact_orders"] == ("channel",)
    assert diff.type_changes["retail.sales.fact_orders"]["order_id"] == (
        "BIGINT",
        "STRING",
    )
    assert "added columns channel" in diff.to_text()


def test_notebook_generation_is_review_first_and_secret_free(tmp_path, uc_client):
    artifacts = generate_uc_ingestion_code(
        source_table="retail.sales.fact_orders",
        include_related=True,
        target_catalog="synthetic_sandbox",
        target_schema="sales_demo",
        rows={"dim_customer": 5, "dim_product": 5, "fact_orders": 20},
        output_path=tmp_path / "retail_pipeline.ipynb",
        seed=42,
        client=uc_client,
    )

    assert set(artifacts) == {
        "notebook",
        "generation_config",
        "relationships",
        "schema_snapshot",
        "validation_report",
        "generation_manifest",
    }
    notebook = json.loads(artifacts["notebook"].read_text(encoding="utf-8"))
    text = json.dumps(notebook)
    assert notebook["nbformat"] == 4
    assert "ENABLE_WRITES = False" in text
    assert "errorifexists" in text
    assert ".mode('overwrite')" not in text.lower()
    assert "token" not in text.lower()


def test_notebook_generation_rejects_source_namespace_and_execution(tmp_path, uc_client):
    with pytest.raises(ValueError, match="must differ"):
        generate_uc_ingestion_code(
            source_table="retail.sales.fact_orders",
            target_catalog="retail",
            target_schema="sales",
            output_path=tmp_path / "unsafe.ipynb",
            client=uc_client,
        )
    with pytest.raises(ValueError, match="never executes writes"):
        generate_uc_ingestion_code(
            source_table="retail.sales.fact_orders",
            target_catalog="synthetic",
            target_schema="sales",
            output_path=tmp_path / "unsafe.ipynb",
            execute=True,
            client=uc_client,
        )


def test_complex_databricks_types_have_clear_diagnostics():
    with pytest.raises(ValueError, match="complex Databricks types"):
        normalize_databricks_type("ARRAY", "ARRAY<STRING>")


def test_metadata_reader_normalizes_columns_constraints_relationships_and_tags():
    client = _QueryFixtureClient()
    metadata = UnityCatalogMetadataReader(client).get_table_metadata("retail.sales.fact_orders")

    assert metadata.name.qualified_name == "retail.sales.fact_orders"
    assert metadata.columns[0].nullable is False
    assert metadata.columns[1].tags == {"semantic": "foreign_key"}
    assert metadata.primary_key_columns == ("order_id",)
    assert metadata.relationships[0].parent_table == "retail.sales.dim_customer"
    assert metadata.tags == {"domain": "retail"}


def test_metadata_reader_reports_missing_or_denied_tables():
    class Missing:
        def query(self, statement):
            return []

    with pytest.raises(UnityCatalogTableNotFoundError, match="not found"):
        UnityCatalogMetadataReader(Missing()).get_table_metadata("retail.sales.missing")

    class Denied:
        def query(self, statement):
            raise UnityCatalogAccessError("permission denied")

    with pytest.raises(UnityCatalogAccessError, match="permission denied"):
        UnityCatalogMetadataReader(Denied()).get_table_metadata("retail.sales.fact_orders")


def test_databricks_sdk_is_lazy_and_missing_dependency_message_is_actionable(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "databricks.sdk":
            raise ImportError("not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ImportError, match=r"great-generator\[databricks\]"):
        DatabricksSDKQueryClient(warehouse_id="abc")


class _QueryFixtureClient:
    def query(self, statement):
        lowered = statement.lower()
        if "information_schema.tables" in lowered:
            return [
                {
                    "TABLE_CATALOG": "retail",
                    "TABLE_SCHEMA": "sales",
                    "TABLE_NAME": "fact_orders",
                    "TABLE_TYPE": "MANAGED",
                    "DATA_SOURCE_FORMAT": "DELTA",
                    "COMMENT": "Orders",
                }
            ]
        if "information_schema.columns" in lowered:
            return [
                {
                    "COLUMN_NAME": "order_id",
                    "ORDINAL_POSITION": 1,
                    "IS_NULLABLE": "NO",
                    "DATA_TYPE": "BIGINT",
                    "FULL_DATA_TYPE": "BIGINT",
                },
                {
                    "COLUMN_NAME": "customer_id",
                    "ORDINAL_POSITION": 2,
                    "IS_NULLABLE": "NO",
                    "DATA_TYPE": "BIGINT",
                    "FULL_DATA_TYPE": "BIGINT",
                },
            ]
        if "information_schema.column_tags" in lowered:
            return [
                {
                    "COLUMN_NAME": "customer_id",
                    "TAG_NAME": "semantic",
                    "TAG_VALUE": "foreign_key",
                }
            ]
        if "information_schema.table_tags" in lowered:
            return [{"TAG_NAME": "domain", "TAG_VALUE": "retail"}]
        if "information_schema.table_constraints" in lowered:
            return [
                {
                    "CONSTRAINT_NAME": "pk_orders",
                    "CONSTRAINT_TYPE": "PRIMARY KEY",
                    "ENFORCED": "NO",
                    "COLUMN_NAME": "order_id",
                    "ORDINAL_POSITION": 1,
                }
            ]
        if "information_schema.referential_constraints" in lowered:
            return [
                {
                    "CONSTRAINT_NAME": "fk_customer",
                    "CHILD_CATALOG": "retail",
                    "CHILD_SCHEMA": "sales",
                    "CHILD_TABLE": "fact_orders",
                    "CHILD_COLUMN": "customer_id",
                    "CHILD_ORDINAL": 1,
                    "PARENT_CATALOG": "retail",
                    "PARENT_SCHEMA": "sales",
                    "PARENT_TABLE": "dim_customer",
                    "PARENT_COLUMN": "customer_id",
                }
            ]
        raise AssertionError(f"Unexpected metadata query: {statement}")


def test_uc_spark_generation_is_distributed_and_relational(uc_client):
    pyspark = pytest.importorskip("pyspark")
    spark = (
        pyspark.sql.SparkSession.builder.master("local[1]")
        .appName("great-generator-uc-tests")
        .getOrCreate()
    )
    try:
        data, report = generate_relational_from_unity_catalog(
            "retail.sales.fact_orders",
            include_related=True,
            rows={"dim_customer": 8, "dim_product": 5, "fact_orders": 30},
            output="spark",
            spark=spark,
            seed=8,
            client=uc_client,
            return_report=True,
        )
        assert data["fact_orders"].count() == 30
        assert data["dim_customer"].count() == 8
        assert report["validation"]["passed"] is True
    finally:
        spark.stop()
