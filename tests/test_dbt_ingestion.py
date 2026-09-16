import json

import pytest

from great_generator import generate_from_dbt_manifest, generate_from_dbt_schema

SCHEMA_YML = """
version: 2

models:
  - name: customers
    description: Customer dimension table
    columns:
      - name: customer_id
        data_type: integer
        description: Unique customer identifier
        tests:
          - unique
          - not_null
      - name: email
        data_type: string
      - name: status
        data_type: string
        tests:
          - accepted_values:
              values: ["ACTIVE", "INACTIVE", "PENDING"]
"""


def test_dbt_schema_yml_model_load(tmp_path):
    path = tmp_path / "schema.yml"
    path.write_text(SCHEMA_YML, encoding="utf-8")

    df = generate_from_dbt_schema(path, model_name="customers", rows=5, seed=42)

    assert len(df) == 5


def test_dbt_schema_yml_columns(tmp_path):
    path = tmp_path / "schema.yml"
    path.write_text(SCHEMA_YML, encoding="utf-8")

    df = generate_from_dbt_schema(path, model_name="customers", rows=5, seed=42)

    assert list(df.columns) == ["customer_id", "email", "status"]


def test_dbt_not_null_mapping(tmp_path):
    path = tmp_path / "schema.yml"
    path.write_text(SCHEMA_YML, encoding="utf-8")

    df = generate_from_dbt_schema(path, model_name="customers", rows=10, seed=42)

    assert df["customer_id"].notna().all()


def test_dbt_unique_mapping(tmp_path):
    path = tmp_path / "schema.yml"
    path.write_text(SCHEMA_YML, encoding="utf-8")

    df = generate_from_dbt_schema(path, model_name="customers", rows=10, seed=42)

    assert df["customer_id"].is_unique


def test_dbt_accepted_values_mapping(tmp_path):
    path = tmp_path / "schema.yml"
    path.write_text(SCHEMA_YML, encoding="utf-8")

    df = generate_from_dbt_schema(path, model_name="customers", rows=9, seed=42)

    assert set(df["status"]).issubset({"ACTIVE", "INACTIVE", "PENDING"})
    assert {"ACTIVE", "INACTIVE", "PENDING"}.issubset(set(df["status"]))


def test_dbt_manifest_model_load(tmp_path):
    manifest = {
        "nodes": {
            "model.demo.customers": {
                "resource_type": "model",
                "name": "customers",
                "columns": {
                    "customer_id": {
                        "name": "customer_id",
                        "data_type": "integer",
                        "tests": ["unique", "not_null"],
                    },
                    "status": {
                        "name": "status",
                        "data_type": "string",
                        "tests": [{"accepted_values": {"values": ["ACTIVE", "INACTIVE"]}}],
                    },
                },
            }
        }
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    df = generate_from_dbt_manifest(path, model_name="customers", rows=4, seed=42)

    assert list(df.columns) == ["customer_id", "status"]
    assert set(df["status"]).issubset({"ACTIVE", "INACTIVE"})


def test_dbt_missing_model_error(tmp_path):
    path = tmp_path / "schema.yml"
    path.write_text(SCHEMA_YML, encoding="utf-8")

    with pytest.raises(ValueError, match="Could not find dbt model 'orders'"):
        generate_from_dbt_schema(path, model_name="orders", rows=5)
