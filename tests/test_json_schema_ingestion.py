import pandas as pd
import pytest

from great_generator import generate_from_json_schema

JSON_SCHEMA = {
    "type": "object",
    "required": ["customer_id", "email"],
    "properties": {
        "customer_id": {"type": "integer"},
        "email": {"type": "string", "format": "email"},
        "signup_date": {"type": "string", "format": "date"},
        "status": {"type": "string", "enum": ["ACTIVE", "INACTIVE", "PENDING"]},
        "balance": {"type": "number", "minimum": 0, "maximum": 10000},
        "is_active": {"type": "boolean"},
    },
}


def test_json_schema_basic_object():
    df = generate_from_json_schema(JSON_SCHEMA, rows=10, seed=42)

    assert list(df.columns) == [
        "customer_id",
        "email",
        "signup_date",
        "status",
        "balance",
        "is_active",
    ]
    assert len(df) == 10


def test_json_schema_required_fields():
    df = generate_from_json_schema(JSON_SCHEMA, rows=25, seed=42)

    assert df["customer_id"].notna().all()
    assert df["email"].notna().all()


def test_json_schema_enum_values():
    df = generate_from_json_schema(JSON_SCHEMA, rows=30, seed=42)

    assert set(df["status"]).issubset({"ACTIVE", "INACTIVE", "PENDING"})
    assert {"ACTIVE", "INACTIVE", "PENDING"}.issubset(set(df["status"]))


def test_json_schema_min_max():
    df = generate_from_json_schema(JSON_SCHEMA, rows=50, seed=42)

    assert df["balance"].between(0, 10000).all()


def test_json_schema_min_max_length():
    schema = {
        "type": "object",
        "properties": {
            "short_code": {"type": "string", "minLength": 3, "maxLength": 5},
        },
    }

    df = generate_from_json_schema(schema, rows=10, seed=42)

    assert df["short_code"].str.len().between(3, 5).all()


def test_json_schema_format_email():
    df = generate_from_json_schema(JSON_SCHEMA, rows=10, seed=42)

    assert df["email"].str.contains("@").all()
    assert df["email"].str.endswith("example.com").all()


def test_json_schema_format_date():
    df = generate_from_json_schema(JSON_SCHEMA, rows=10, seed=42)

    assert pd.to_datetime(df["signup_date"], errors="coerce").notna().all()


def test_json_schema_unsupported_keyword_diagnostics():
    schema = {
        "type": "object",
        "oneOf": [],
        "properties": {"id": {"type": "integer"}},
    }

    with pytest.raises(ValueError, match="Unsupported JSON Schema features"):
        generate_from_json_schema(schema, rows=5)


def test_json_schema_seed_determinism():
    first = generate_from_json_schema(JSON_SCHEMA, rows=12, seed=2026)
    second = generate_from_json_schema(JSON_SCHEMA, rows=12, seed=2026)

    pd.testing.assert_frame_equal(first, second)
