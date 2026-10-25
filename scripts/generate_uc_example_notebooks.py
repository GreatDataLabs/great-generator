"""Regenerate the offline-first Unity Catalog example notebooks."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "examples" / "databricks" / "unity_catalog"

COMMON = """from pathlib import Path

from great_generator import StaticUnityCatalogClient

SOURCE_TABLE = "retail.sales.fact_orders"
FIXTURE = Path("examples/databricks/unity_catalog/mock_uc_metadata.json")
client = StaticUnityCatalogClient.from_path(FIXTURE)

# In a Databricks workspace, remove client=client and pass spark=spark instead.
"""


NOTEBOOKS = {
    "01_inspect_uc_table.ipynb": (
        "Inspect Unity Catalog metadata",
        """from great_generator import inspect_unity_catalog_table

snapshot = inspect_unity_catalog_table(
    SOURCE_TABLE,
    include_related=True,
    related_direction="parents",
    client=client,
)
snapshot.as_dict()
""",
        """assert snapshot.metadata_only_source_read is True
assert len(snapshot.tables) == 3
assert len(snapshot.relationships) == 2
""",
    ),
    "02_generate_single_uc_table.ipynb": (
        "Generate one UC-derived synthetic table",
        """from great_generator import generate_from_unity_catalog

df = generate_from_unity_catalog(
    "retail.sales.dim_customer",
    rows=100,
    seed=42,
    client=client,
)
df.head()
""",
        """assert len(df) == 100
assert df["customer_id"].is_unique
""",
    ),
    "03_generate_related_tables.ipynb": (
        "Generate declared related tables",
        """from great_generator import generate_relational_from_unity_catalog

datasets, report = generate_relational_from_unity_catalog(
    SOURCE_TABLE,
    include_related=True,
    rows={"dim_customer": 25, "dim_product": 10, "fact_orders": 200},
    seed=42,
    client=client,
    return_report=True,
)
{name: len(frame) for name, frame in datasets.items()}
""",
        """assert report["validation"]["passed"] is True
assert datasets["fact_orders"]["customer_id"].isin(
    datasets["dim_customer"]["customer_id"]
).all()
""",
    ),
    "04_generate_star_schema.ipynb": (
        "Build a star-schema-shaped synthetic dataset",
        """from great_generator import generate_relational_from_unity_catalog

star = generate_relational_from_unity_catalog(
    SOURCE_TABLE,
    include_related=True,
    related_direction="parents",
    rows={"dim_customer": 50, "dim_product": 20, "fact_orders": 500},
    seed=2026,
    client=client,
)
sorted(star)
""",
        """assert set(star) == {"dim_customer", "dim_product", "fact_orders"}
# Naming is a hint only; declared relationships establish the graph.
""",
    ),
    "05_generate_scd2_dimension.ipynb": (
        "Generate explicit SCD Type 2 history",
        """from great_generator import generate_relational_from_unity_catalog

datasets = generate_relational_from_unity_catalog(
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
    rows=25,
    seed=42,
    client=client,
)
history = datasets["dim_customer_history"]
history.head()
""",
        """assert history.groupby("customer_id")["is_current"].sum().eq(1).all()
assert (history["effective_start_date"] < history["effective_end_date"]).all()
""",
    ),
    "06_generate_cdc_events.ipynb": (
        "Generate portable synthetic CDC events",
        """from great_generator import generate_uc_cdc

cdc = generate_uc_cdc(
    SOURCE_TABLE,
    rows=100,
    operations={"INSERT": 0.7, "UPDATE": 0.2, "DELETE": 0.1},
    seed=42,
    client=client,
)
cdc.head()
""",
        """assert cdc["sequence_number"].is_monotonic_increasing
assert set(cdc["operation"]).issubset({"INSERT", "UPDATE", "DELETE"})
# Portable events are not represented as actual Delta Change Data Feed rows.
""",
    ),
    "07_generate_query_aware_data.ipynb": (
        "Generate query-aware UC-derived data",
        """from great_generator import generate_from_unity_catalog

df = generate_from_unity_catalog(
    "retail.sales.dim_customer",
    rows=100,
    required_values={"region": ["EAST", "WEST"]},
    seed=42,
    client=client,
)
df["region"].value_counts()
""",
        """assert {"EAST", "WEST"}.issubset(set(df["region"]))
# Query-aware values improve coverage; they do not guarantee production performance.
""",
    ),
    "08_generate_anomaly_test_data.ipynb": (
        "Generate an explicit anomaly test pack",
        """from great_generator import generate_relational_from_unity_catalog

datasets, report = generate_relational_from_unity_catalog(
    SOURCE_TABLE,
    include_related=True,
    rows={"dim_customer": 25, "dim_product": 10, "fact_orders": 200},
    anomalies={"duplicate_rate": 0.02, "orphan_fk_rate": 0.01},
    seed=42,
    client=client,
    return_report=True,
)
report["validation"]
""",
        """assert report["validation"]["expected_anomalies"]
# Clean generation is the default; violations appear only when requested.
""",
    ),
    "09_generate_ingestion_notebook.ipynb": (
        "Generate a review-first Databricks ingestion notebook",
        """from tempfile import TemporaryDirectory

from great_generator import generate_uc_ingestion_code

with TemporaryDirectory() as output_dir:
    artifacts = generate_uc_ingestion_code(
        source_table=SOURCE_TABLE,
        include_related=True,
        target_catalog="synthetic_sandbox",
        target_schema="sales_demo",
        rows={"dim_customer": 25, "dim_product": 10, "fact_orders": 200},
        output_path=Path(output_dir) / "retail_pipeline.ipynb",
        seed=42,
        execute=False,
        client=client,
    )
    print(sorted(artifacts))
""",
        """assert "notebook" in artifacts
# Generated writes are disabled and use error-if-exists semantics.
""",
    ),
    "10_validate_relational_integrity.ipynb": (
        "Validate UC-derived relational integrity",
        """from great_generator import generate_relational_from_unity_catalog

datasets, report = generate_relational_from_unity_catalog(
    SOURCE_TABLE,
    include_related=True,
    rows={"dim_customer": 25, "dim_product": 10, "fact_orders": 200},
    seed=42,
    client=client,
    return_report=True,
)
report["validation"]
""",
        """assert report["validation"]["passed"] is True
assert all(
    not check.get("checked") or check.get("passed")
    for check in report["validation"]["foreign_keys"].values()
)
""",
    ),
    "11_detect_uc_schema_changes.ipynb": (
        "Detect Unity Catalog schema changes",
        """from copy import deepcopy

from great_generator import UnityCatalogSnapshot, compare_uc_schema_snapshots

old = client.snapshot
payload = deepcopy(old.as_dict())
payload["tables"][SOURCE_TABLE]["columns"].append({
    "name": "channel",
    "position": 8,
    "data_type": "STRING",
    "nullable": True,
})
new = UnityCatalogSnapshot.from_dict(payload)
diff = compare_uc_schema_snapshots(old, new)
print(diff.to_text())
""",
        """assert diff.changed is True
assert diff.added_columns[SOURCE_TABLE] == ("channel",)
# Snapshot comparison reports drift; it never migrates source schemas.
""",
    ),
}


def markdown(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(True)}


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(True),
    }


def build(title: str, example: str, validation: str) -> dict:
    return {
        "cells": [
            markdown(
                f"# {title}\n\n"
                "Offline path: use the included metadata-only fixture. Databricks path: use the "
                "active `spark` session. No credentials or source records are embedded."
            ),
            markdown(
                "## Prerequisites\n\n"
                "Install `great-generator`. For SDK access outside a notebook, install "
                "`great-generator[databricks]` and use Databricks unified authentication. "
                "Metadata visibility and source object permissions are controlled by Unity "
                "Catalog."
            ),
            code(COMMON),
            markdown("## Generate synthetic data from metadata"),
            code(example),
            markdown("## Validate"),
            code(validation),
            markdown(
                "## Cleanup and limitations\n\n"
                "These examples do not write tables. Remove only sandbox artifacts you explicitly "
                "create. Generated data is synthetic, not anonymized production data. Complex "
                "types and cyclic/self-referencing relationships require explicit modeling."
            ),
        ],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for filename, (title, example, validation) in NOTEBOOKS.items():
        (OUTPUT / filename).write_text(
            json.dumps(build(title, example, validation), indent=2) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
