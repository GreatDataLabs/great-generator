from __future__ import annotations

# ruff: noqa: E402,I001

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from great_generator import (
    export_dataset,
    generate_relational,
    validate_query_coverage,
)  # noqa: E402

TABLES = {
    "dim_customer": {
        "schema": "customer_id int primary key, region string, customer_segment string, signup_date date",
        "base_rows": 10000,
    },
    "dim_product": {
        "schema": "product_id int primary key, product_category string, brand string",
        "base_rows": 1000,
    },
    "dim_store": {
        "schema": "store_id int primary key, region string, store_type string",
        "base_rows": 250,
    },
    "dim_date": {
        "schema": "date_id int primary key, business_date date, month_id string",
        "base_rows": 366,
    },
    "fact_sales": {
        "schema": "sales_id int primary key, customer_id int references dim_customer.customer_id, product_id int references dim_product.product_id, store_id int references dim_store.store_id, date_id int references dim_date.date_id, business_date date, region string, product_category string, sales_channel string, quantity int, sales_amount double",
        "base_rows": 100000,
    },
}
RELATIONSHIPS = [
    "fact_sales.customer_id -> dim_customer.customer_id",
    "fact_sales.product_id -> dim_product.product_id",
    "fact_sales.store_id -> dim_store.store_id",
    "fact_sales.date_id -> dim_date.date_id",
]
REQUIRED_VALUES = {
    "fact_sales.region": ["SOUTH"],
    "fact_sales.product_category": ["ELECTRONICS", "GROCERY"],
    "fact_sales.sales_channel": ["ONLINE", "STORE"],
}
PARTITION_BY = {
    "table": "fact_sales",
    "column": "business_date",
    "values": [
        "2026-01-01",
        "2026-01-02",
        "2026-01-03",
        "2026-01-04",
        "2026-01-05",
        "2026-01-06",
        "2026-01-07",
    ],
    "distribution": "balanced",
}
TARGET_SELECTIVITY = {
    "fact_sales.region": {"SOUTH": 0.25},
    "fact_sales.sales_channel": {"ONLINE": 0.35},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the Great Generator retail star schema benchmark dataset."
    )
    parser.add_argument("--output", default="output/retail_star_schema", help="Output folder.")
    parser.add_argument("--format", default="parquet", choices=["csv", "jsonl", "parquet"])
    parser.add_argument("--scale-factor", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def scaled_rows(scale_factor: float) -> dict[str, int]:
    if scale_factor <= 0:
        raise SystemExit("--scale-factor must be greater than zero.")
    return {name: max(1, int(spec["base_rows"] * scale_factor)) for name, spec in TABLES.items()}


def table_specs() -> dict[str, dict[str, Any]]:
    return {name: {"schema": spec["schema"]} for name, spec in TABLES.items()}


def main() -> None:
    args = parse_args()
    rows = scaled_rows(args.scale_factor)
    output = Path(args.output)
    data = generate_relational(
        tables=table_specs(),
        rows=rows,
        relationships=RELATIONSHIPS,
        required_values=REQUIRED_VALUES,
        partition_by=PARTITION_BY,
        target_selectivity=TARGET_SELECTIVITY,
        seed=args.seed,
    )
    written = export_dataset(data, output, format=args.format, overwrite=args.overwrite)
    coverage = validate_query_coverage(
        data,
        required_values=REQUIRED_VALUES,
        partition_by=PARTITION_BY,
        target_selectivity=TARGET_SELECTIVITY,
        relationships=RELATIONSHIPS,
    )
    manifest = {
        "dataset": "retail_star_schema",
        "format": args.format,
        "scale_factor": args.scale_factor,
        "seed": args.seed,
        "rows": {name: int(len(frame)) for name, frame in data.items()},
        "written": written,
        "coverage": coverage,
        "limitations": "Benchmark outputs are synthetic and environment-specific. They are not universal performance claims.",
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "generation_manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str), encoding="utf-8"
    )
    print(
        json.dumps(
            {"dataset": manifest["dataset"], "rows": manifest["rows"], "output": str(output)},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
