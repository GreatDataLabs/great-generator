import pandas as pd
import pytest

from great_generator import generate_nested


def test_nested_two_level_auto_fk():
    """Two-level nesting, FK auto-inferred."""
    spec = {
        "faculty": {
            "schema": "faculty_id int primary key, name string",
            "rows": 10,
            "children": {
                "subject": {
                    "schema": "subject_id int primary key, title string",
                    "rows": 20,
                }
            },
        }
    }
    data = generate_nested(spec)

    assert "faculty" in data
    assert "subject" in data
    assert "faculty_id" in data["subject"].columns
    assert len(data["faculty"]) == 10
    assert len(data["subject"]) == 20


def test_nested_two_level_explicit_fk():
    """Two-level nesting, FK explicit."""
    spec = {
        "faculty": {
            "schema": "faculty_id int primary key, name string",
            "rows": 10,
            "children": {
                "subject": {
                    "schema": "subject_id int primary key, title string",
                    "rows": 20,
                    "fk": "fac_id",
                }
            },
        }
    }
    data = generate_nested(spec)

    assert "fac_id" in data["subject"].columns
    assert "faculty_id" not in data["subject"].columns


def test_nested_three_level():
    """Three-level nesting (grandparent -> parent -> child)."""
    spec = {
        "faculty": {
            "schema": "faculty_id int primary key, name string",
            "rows": 5,
            "children": {
                "subject": {
                    "schema": "subject_id int primary key, title string",
                    "rows": 10,
                    "children": {
                        "enrollment": {
                            "schema": "enrollment_id int primary key, grade string",
                            "rows": 20,
                        }
                    },
                }
            },
        }
    }
    data = generate_nested(spec)

    assert "faculty" in data
    assert "subject" in data
    assert "enrollment" in data
    assert "faculty_id" in data["subject"].columns
    assert "subject_id" in data["enrollment"].columns


def test_nested_fk_already_present():
    """FK column already present in child schema (no duplicate injection)."""
    spec = {
        "faculty": {
            "schema": "faculty_id int primary key, name string",
            "rows": 5,
            "children": {
                "subject": {
                    "schema": "subject_id int primary key, faculty_id int, title string",
                    "rows": 10,
                }
            },
        }
    }
    data = generate_nested(spec)

    # Should not have "faculty_id int, faculty_id int" or similar duplication
    # Check if column exists only once
    cols = data["subject"].columns.tolist()
    assert cols.count("faculty_id") == 1


def test_nested_top_level_no_children():
    """Top-level tables with no children (passthrough)."""
    spec = {
        "student": {"schema": "student_id int primary key, name string", "rows": 10},
        "course": {"schema": "course_id int primary key, name string", "rows": 5},
    }
    data = generate_nested(spec)

    assert "student" in data
    assert "course" in data
    assert len(data["student"]) == 10
    assert len(data["course"]) == 5


def test_nested_invalid_missing_schema():
    """Invalid nesting (missing schema key) raises a clear ValueError."""
    spec = {
        "faculty": {
            "rows": 10,  # missing schema
        }
    }
    with pytest.raises(ValueError, match="missing the required 'schema' key"):
        generate_nested(spec)


def test_nested_row_counts_respected():
    """Row counts respected per-node."""
    spec = {
        "faculty": {
            "schema": "faculty_id int primary key, name string",
            "rows": 15,
            "children": {
                "subject": {
                    "schema": "subject_id int primary key, title string",
                    "rows": 42,
                }
            },
        }
    }
    data = generate_nested(spec)

    assert len(data["faculty"]) == 15
    assert len(data["subject"]) == 42


def test_nested_seed_deterministic():
    """seed produces deterministic output."""
    spec = {
        "faculty": {
            "schema": "faculty_id int primary key, name string",
            "rows": 10,
            "children": {
                "subject": {
                    "schema": "subject_id int primary key, title string",
                    "rows": 20,
                }
            },
        }
    }
    data1 = generate_nested(spec, seed=42)
    data2 = generate_nested(spec, seed=42)

    pd.testing.assert_frame_equal(data1["faculty"], data2["faculty"])
    pd.testing.assert_frame_equal(data1["subject"], data2["subject"])


def test_nested_custom_parent_primary_key():
    spec = {
        "faculty": {
            "schema": "faculty_key int primary key, name string",
            "rows": 5,
            "children": {
                "subject": {"schema": "subject_id int primary key, title string", "rows": 10}
            },
        }
    }

    data = generate_nested(spec, seed=7)

    assert "faculty_key" in data["faculty"].columns
    assert "faculty_id" in data["subject"].columns
    assert set(data["subject"]["faculty_id"]).issubset(set(data["faculty"]["faculty_key"]))


def test_nested_custom_foreign_key():
    spec = {
        "faculty": {
            "schema": "faculty_id int primary key",
            "children": {
                "subject": {
                    "schema": "subject_id int primary key, title string",
                    "fk": "faculty_ref",
                }
            },
        }
    }

    data = generate_nested(spec, seed=7)
    assert "faculty_ref" in data["subject"].columns


def test_nested_invalid_children_type():
    spec = {"faculty": {"schema": "faculty_id int primary key", "children": None}}

    with pytest.raises(ValueError, match="'children' must be a mapping"):
        generate_nested(spec)


def test_nested_duplicate_table_name():
    spec = {
        "faculty": {
            "schema": "faculty_id int primary key",
            "children": {"subject": {"schema": "subject_id int primary key"}},
        },
        "subject": {"schema": "subject_id int primary key"},
    }

    with pytest.raises(ValueError, match="Duplicate table name 'subject'"):
        generate_nested(spec)


def test_nested_existing_foreign_key_is_used_for_generation():
    spec = {
        "faculty": {
            "schema": "faculty_id int primary key",
            "rows": 5,
            "children": {
                "subject": {
                    "schema": "subject_id int primary key, faculty_id int",
                    "rows": 20,
                }
            },
        }
    }

    data = generate_nested(spec, seed=11)

    assert set(data["subject"]["faculty_id"]).issubset(set(data["faculty"]["faculty_id"]))
    assert data["subject"]["faculty_id"].nunique() <= 5


def test_nested_existing_foreign_key_type_mismatch():
    spec = {
        "faculty": {
            "schema": "faculty_id int primary key",
            "children": {
                "subject": {
                    "schema": "subject_id int primary key, faculty_id string",
                }
            },
        }
    }

    with pytest.raises(ValueError, match="has type 'string'.*has type 'int'"):
        generate_nested(spec)
