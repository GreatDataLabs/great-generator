"""Validate platform examples without requiring platform credentials.

The script checks that expected example assets exist, notebooks are valid JSON,
notebooks reference Great Generator where appropriate, and example text avoids
obvious credential material or benchmark-ranking claims.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_FILES = [
    "examples/pandas/01_generate_from_schema.ipynb",
    "examples/pandas/02_generate_from_json_schema.ipynb",
    "examples/pandas/03_generate_from_dbt_schema.ipynb",
    "examples/pandas/04_generate_from_data_dictionary.ipynb",
    "examples/pandas/05_relational_generation.ipynb",
    "examples/pandas/06_query_aware_generation.ipynb",
    "examples/pandas/07_cdc_anomaly_generation.ipynb",
    "examples/pandas/README.md",
    "examples/databricks/01_generate_from_schema_delta.ipynb",
    "examples/databricks/02_generate_from_json_schema_delta.ipynb",
    "examples/databricks/03_relational_star_schema_delta.ipynb",
    "examples/databricks/04_query_aware_partition_test.ipynb",
    "examples/databricks/05_cdc_anomaly_lakehouse_demo.ipynb",
    "examples/databricks/06_write_to_unity_catalog_volume.ipynb",
    "examples/databricks/README.md",
    "examples/fabric/01_generate_from_schema_lakehouse.ipynb",
    "examples/fabric/02_generate_parquet_to_onelake.ipynb",
    "examples/fabric/03_relational_lakehouse_demo.ipynb",
    "examples/fabric/04_query_aware_fabric_warehouse_demo.ipynb",
    "examples/fabric/README.md",
    "examples/snowflake/01_generate_parquet_for_snowflake.ipynb",
    "examples/snowflake/02_stage_and_copy_into_snowflake.sql",
    "examples/snowflake/03_query_aware_snowflake_test.sql",
    "examples/snowflake/README.md",
    "examples/cloud_storage/01_write_to_s3.ipynb",
    "examples/cloud_storage/02_write_to_adls.ipynb",
    "examples/cloud_storage/03_write_to_gcs.ipynb",
    "examples/cloud_storage/README.md",
    "benchmarks/README.md",
    "benchmarks/datasets/retail_star_schema/schema.yml",
    "benchmarks/datasets/retail_star_schema/query_profile.yml",
    "benchmarks/datasets/retail_star_schema/generate_dataset.py",
    "benchmarks/queries/retail_star_schema/q01_partition_filter.sql",
    "benchmarks/queries/retail_star_schema/q02_join_aggregation.sql",
    "benchmarks/queries/retail_star_schema/q03_selectivity_filter.sql",
    "benchmarks/queries/retail_star_schema/q04_monthly_rollup.sql",
    "benchmarks/queries/retail_star_schema/q05_large_groupby.sql",
    "benchmarks/results_template/benchmark_results_template.csv",
    "benchmarks/results_template/benchmark_report_template.md",
    "docs/PLATFORM_EXAMPLES.md",
    "docs/CLOUD_EXPORTS.md",
    "docs/BENCHMARK_HARNESS.md",
]

SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)(aws_secret_access_key|client_secret|private_key)\s*=\s*['\"][^'\"]+['\"]"),
    re.compile(r"(?i)snowflake://[^\s]+:[^\s]+@"),
]

RANKING_PATTERNS = [
    re.compile(r"(?i)databricks\s+is\s+faster\s+than\s+snowflake"),
    re.compile(r"(?i)snowflake\s+is\s+faster\s+than\s+databricks"),
    re.compile(r"(?i)fabric\s+is\s+slower\s+than\s+databricks"),
    re.compile(r"(?i)best\s+performing\s+platform"),
]

PRIVATE_PATH_PATTERNS = [
    re.compile(r"dbfs:/Users/", re.IGNORECASE),
    re.compile(r"/Workspace/Users/", re.IGNORECASE),
]


def read_text(path: Path) -> str:
    if path.suffix == ".ipynb":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return "\n".join("".join(cell.get("source", [])) for cell in payload.get("cells", []))
    return path.read_text(encoding="utf-8")


def validate_expected_files() -> list[str]:
    errors: list[str] = []
    for relative in EXPECTED_FILES:
        path = ROOT / relative
        if not path.exists():
            errors.append(f"Missing expected example file: {relative}")
    return errors


def validate_notebooks() -> list[str]:
    errors: list[str] = []
    for path in sorted((ROOT / "examples").rglob("*.ipynb")) + sorted(
        (ROOT / "benchmarks").rglob("*.ipynb")
    ):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("nbformat") != 4:
            errors.append(f"Notebook must be nbformat 4: {path.relative_to(ROOT)}")
        text = read_text(path)
        if "great_generator" not in text and "great-generator" not in text:
            errors.append(f"Notebook should reference Great Generator: {path.relative_to(ROOT)}")
    return errors


def validate_content_hygiene() -> list[str]:
    errors: list[str] = []
    search_roots = [ROOT / "examples", ROOT / "benchmarks", ROOT / "docs"]
    for base in search_roots:
        for path in base.rglob("*"):
            if path.is_dir() or path.suffix.lower() in {".png", ".jpg", ".jpeg", ".pyc"}:
                continue
            text = (
                read_text(path)
                if path.suffix == ".ipynb"
                else path.read_text(encoding="utf-8", errors="ignore")
            )
            for pattern in SECRET_PATTERNS:
                if pattern.search(text):
                    errors.append(f"Potential secret-like content in {path.relative_to(ROOT)}")
            for pattern in PRIVATE_PATH_PATTERNS:
                if pattern.search(text):
                    errors.append(f"Private workspace path in {path.relative_to(ROOT)}")
            for pattern in RANKING_PATTERNS:
                if pattern.search(text):
                    errors.append(
                        f"Unsupported benchmark ranking claim in {path.relative_to(ROOT)}"
                    )
    return errors


def main() -> int:
    errors = []
    errors.extend(validate_expected_files())
    errors.extend(validate_notebooks())
    errors.extend(validate_content_hygiene())
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Example validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
