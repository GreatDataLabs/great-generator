import json

import pytest

from great_generator import generate_from_data_dictionary, load_data_dictionary

CSV_TEXT = """column_name,data_type,nullable,description,allowed_values,min,max,unique
customer_id,integer,false,Unique customer identifier,,,,true
email,string,false,Customer email address,,,,true
status,string,false,Customer account status,ACTIVE|INACTIVE|PENDING,,,
balance,decimal,true,Current balance,,0,10000,
"""


def test_data_dictionary_csv_load(tmp_path):
    path = tmp_path / "dictionary.csv"
    path.write_text(CSV_TEXT, encoding="utf-8")

    schema = load_data_dictionary(path)

    assert schema == {
        "customer_id": "int",
        "email": "string",
        "status": "string",
        "balance": "float",
    }


def test_data_dictionary_allowed_values(tmp_path):
    path = tmp_path / "dictionary.csv"
    path.write_text(CSV_TEXT, encoding="utf-8")

    df = generate_from_data_dictionary(path, rows=9, seed=42)

    assert set(df["status"]).issubset({"ACTIVE", "INACTIVE", "PENDING"})
    assert {"ACTIVE", "INACTIVE", "PENDING"}.issubset(set(df["status"]))


def test_data_dictionary_min_max(tmp_path):
    path = tmp_path / "dictionary.csv"
    path.write_text(CSV_TEXT, encoding="utf-8")

    df = generate_from_data_dictionary(path, rows=20, seed=42)

    assert df["balance"].between(0, 10000).all()


def test_data_dictionary_nullable(tmp_path):
    path = tmp_path / "dictionary.csv"
    path.write_text(CSV_TEXT, encoding="utf-8")

    df = generate_from_data_dictionary(path, rows=20, seed=42)

    assert df["customer_id"].notna().all()
    assert df["email"].notna().all()


def test_data_dictionary_unique(tmp_path):
    path = tmp_path / "dictionary.csv"
    path.write_text(CSV_TEXT, encoding="utf-8")

    df = generate_from_data_dictionary(path, rows=20, seed=42)

    assert df["customer_id"].is_unique
    assert df["email"].is_unique


def test_data_dictionary_yaml_load(tmp_path):
    yaml = pytest.importorskip("yaml")
    path = tmp_path / "dictionary.yml"
    path.write_text(
        yaml.safe_dump(
            {
                "columns": [
                    {"column_name": "customer_id", "data_type": "integer", "unique": True},
                    {"column_name": "status", "data_type": "string", "allowed_values": ["A", "I"]},
                ]
            }
        ),
        encoding="utf-8",
    )

    df = generate_from_data_dictionary(path, rows=4, seed=42)

    assert list(df.columns) == ["customer_id", "status"]
    assert set(df["status"]).issubset({"A", "I"})


def test_data_dictionary_json_load(tmp_path):
    path = tmp_path / "dictionary.json"
    path.write_text(
        json.dumps(
            {
                "columns": [
                    {"column_name": "customer_id", "data_type": "integer"},
                    {"column_name": "balance", "data_type": "decimal", "min": 0, "max": 10},
                ]
            }
        ),
        encoding="utf-8",
    )

    df = generate_from_data_dictionary(path, rows=4, seed=42)

    assert list(df.columns) == ["customer_id", "balance"]
    assert df["balance"].between(0, 10).all()


def test_data_dictionary_missing_column_name_error(tmp_path):
    path = tmp_path / "dictionary.csv"
    path.write_text("data_type\ninteger\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing column_name"):
        generate_from_data_dictionary(path, rows=5)
