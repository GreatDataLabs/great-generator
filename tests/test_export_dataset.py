from __future__ import annotations

import pandas as pd
import pytest

from great_generator import export_dataset


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "customer_id": [1, 2, 3],
            "customer_name": ["Ava", "Ben", "Chandra"],
            "balance": [10.5, 20.25, 0.0],
        }
    )


def test_export_dataset_csv_local(tmp_path):
    output = tmp_path / "customers"

    written = export_dataset(_frame(), output, format="csv")

    assert written == [str(output.with_suffix(".csv"))]
    exported = pd.read_csv(written[0])
    assert list(exported.columns) == ["customer_id", "customer_name", "balance"]
    assert len(exported) == 3


def test_export_dataset_jsonl_local(tmp_path):
    output = tmp_path / "customers"

    written = export_dataset(_frame(), output, format="jsonl")

    assert written == [str(output.with_suffix(".jsonl"))]
    exported = pd.read_json(written[0], lines=True)
    assert exported["customer_name"].tolist() == ["Ava", "Ben", "Chandra"]


def test_export_dataset_parquet_local_if_dependency_available(tmp_path):
    pytest.importorskip("pyarrow")
    output = tmp_path / "customers"

    written = export_dataset(_frame(), output, format="parquet")

    assert written == [str(output.with_suffix(".parquet"))]
    exported = pd.read_parquet(written[0])
    pd.testing.assert_frame_equal(exported, _frame())


def test_export_dataset_mapping_writes_table_folders(tmp_path):
    output = tmp_path / "dataset"

    written = export_dataset({"customers": _frame()}, output, format="csv")

    assert written == [str(output / "customers" / "customers.csv")]
    assert (output / "customers" / "customers.csv").exists()


def test_export_dataset_rejects_unknown_format(tmp_path):
    with pytest.raises(ValueError, match="Unsupported export format"):
        export_dataset(_frame(), tmp_path / "customers", format="xlsx")


def test_export_dataset_does_not_overwrite_by_default(tmp_path):
    output = tmp_path / "customers"
    export_dataset(_frame(), output, format="csv")

    with pytest.raises(FileExistsError, match="already exists"):
        export_dataset(_frame(), output, format="csv")


def test_export_dataset_overwrite_true(tmp_path):
    output = tmp_path / "customers"
    export_dataset(_frame(), output, format="csv")

    written = export_dataset(_frame().head(1), output, format="csv", overwrite=True)

    exported = pd.read_csv(written[0])
    assert len(exported) == 1


def test_export_dataset_mode_overwrite(tmp_path):
    output = tmp_path / "customers"
    export_dataset(_frame(), output, format="jsonl")

    written = export_dataset(_frame().head(2), output, format="json", mode="overwrite")

    exported = pd.read_json(written[0], lines=True)
    assert len(exported) == 2
