from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pandas as pd
import pytest

from great_generator import generate_hf_dataset_card, to_hf_dataset, to_hf_dataset_dict


def _install_fake_datasets(monkeypatch):
    module = ModuleType("datasets")

    class FakeDataset:
        def __init__(self, frame, preserve_index):
            self.frame = frame
            self.preserve_index = preserve_index
            self.info = SimpleNamespace(description="", citation="", homepage="", license="")

        @classmethod
        def from_pandas(cls, frame, preserve_index=False):
            return cls(frame.copy(), preserve_index)

    class FakeDatasetDict(dict):
        pass

    module.Dataset = FakeDataset
    module.DatasetDict = FakeDatasetDict
    monkeypatch.setitem(sys.modules, "datasets", module)
    return FakeDataset, FakeDatasetDict


def test_to_hf_dataset_converts_pandas_dataframe(monkeypatch):
    FakeDataset, _ = _install_fake_datasets(monkeypatch)
    df = pd.DataFrame({"customer_id": [1, 2], "email": ["a@example.com", "b@example.com"]})

    dataset = to_hf_dataset(df)

    assert isinstance(dataset, FakeDataset)
    pd.testing.assert_frame_equal(dataset.frame, df)
    assert dataset.preserve_index is False


def test_to_hf_dataset_preserve_index_and_metadata(monkeypatch):
    _install_fake_datasets(monkeypatch)
    df = pd.DataFrame({"value": [10, 20]}, index=pd.Index(["a", "b"], name="row_id"))

    dataset = to_hf_dataset(
        df,
        preserve_index=True,
        metadata={"description": "Synthetic sample", "license": "MIT"},
    )

    assert dataset.preserve_index is True
    assert dataset.info.description == "Synthetic sample"
    assert dataset.info.license == "MIT"
    assert dataset.great_generator_metadata["description"] == "Synthetic sample"


def test_to_hf_dataset_dict_converts_related_tables(monkeypatch):
    FakeDataset, FakeDatasetDict = _install_fake_datasets(monkeypatch)
    tables = {
        "customers": pd.DataFrame({"customer_id": [1]}),
        "orders": pd.DataFrame({"order_id": [10], "customer_id": [1]}),
    }

    dataset_dict = to_hf_dataset_dict(tables)

    assert isinstance(dataset_dict, FakeDatasetDict)
    assert set(dataset_dict) == {"customers", "orders"}
    assert all(isinstance(value, FakeDataset) for value in dataset_dict.values())


def test_to_hf_dataset_missing_dependency_gives_clear_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "datasets", None)

    with pytest.raises(ImportError, match=r"great-generator\[hf\]"):
        to_hf_dataset(pd.DataFrame({"a": [1]}))


def test_to_hf_dataset_rejects_non_dataframe(monkeypatch):
    _install_fake_datasets(monkeypatch)

    with pytest.raises(TypeError, match="pandas DataFrame"):
        to_hf_dataset([{"a": 1}])


def test_dataset_card_includes_required_synthetic_notice():
    card = generate_hf_dataset_card(
        dataset_name="synthetic-retail-star-schema",
        domain="retail",
        row_counts={"dim_customer": 100, "fact_sales": 1000},
        seed=42,
    )

    assert "This dataset is synthetic" in card
    assert "not production data" in card
    assert "not an anonymized, masked, or de-identified copy" in card


def test_dataset_card_includes_row_counts_and_uses():
    card = generate_hf_dataset_card(
        dataset_name="synthetic-customers",
        row_counts={"customers": 10},
        intended_use=["QA testing"],
        not_intended_use=["production scoring"],
        limitations=["Synthetic data only"],
    )

    assert "| customers | 10 |" in card
    assert "- QA testing" in card
    assert "- production scoring" in card
    assert "- Synthetic data only" in card


def test_dataset_card_is_markdown_and_avoids_privacy_claims():
    card = generate_hf_dataset_card(dataset_name="synthetic-demo")

    assert card.startswith("---\n")
    assert "# synthetic-demo" in card
    assert "privacy guarantee" not in card.lower()
    assert "production data" in card
