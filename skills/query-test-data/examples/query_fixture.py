"""Marginal coverage plus execution of one known, read-only SQL query in memory."""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import date
from importlib.metadata import version

import pandas as pd

from great_generator import generate_relational, validate_query_coverage
from great_generator.io.manifest import build_generation_manifest

TABLES = {
    "dim_customer": {"schema": "customer_id int primary key, region string", "rows": 8},
    "dim_product": {"schema": "product_id int primary key, product_type string", "rows": 4},
    "fact_transactions": {
        "schema": (
            "transaction_id int primary key, "
            "customer_id int references dim_customer.customer_id, "
            "product_id int references dim_product.product_id, business_date date, amount double"
        ),
        "rows": 120,
    },
}
RELATIONSHIPS = [
    "fact_transactions.customer_id -> dim_customer.customer_id",
    "fact_transactions.product_id -> dim_product.product_id",
]
PROFILE = {
    "required_values": {
        "dim_customer.region": ["SOUTH"],
        "dim_product.product_type": ["CHECKING", "SAVINGS"],
    },
    "target_selectivity": {
        "dim_customer.region": {"SOUTH": 1.0},
        "dim_product.product_type": {"CHECKING": 0.5, "SAVINGS": 0.5},
    },
    "partition_by": {
        "table": "fact_transactions",
        "column": "business_date",
        "values": [f"2026-10-{day:02d}" for day in range(1, 16)],
        "distribution": "balanced",
    },
    "ensure_join_coverage": True,
}
SQL = """
SELECT c.region, p.product_type, SUM(f.amount) AS total_amount
FROM fact_transactions f
JOIN dim_customer c ON f.customer_id = c.customer_id
JOIN dim_product p ON f.product_id = p.product_id
WHERE f.business_date BETWEEN '2026-10-01' AND '2026-10-15'
  AND c.region = 'SOUTH' AND p.product_type IN ('CHECKING', 'SAVINGS')
GROUP BY c.region, p.product_type
"""


def build_fixture(seed=42):
    data = generate_relational(TABLES, query_profile=PROFILE, seed=seed)
    report = validate_query_coverage(data, query_profile=PROFILE, relationships=RELATIONSHIPS)
    # Only this checked-in SELECT is executed. Never execute arbitrary supplied SQL automatically.
    with sqlite3.connect(":memory:") as connection:
        for name, frame in data.items():
            serializable = frame.copy()
            if "business_date" in serializable:
                serializable["business_date"] = pd.to_datetime(
                    serializable["business_date"]
                ).dt.strftime("%Y-%m-%d")
            serializable.to_sql(name, connection, index=False)
        result = pd.read_sql_query(SQL, connection)
    report["query_assertions"] = {
        "both_product_groups": set(result.product_type) == {"CHECKING", "SAVINGS"},
        "only_south": set(result.region) == {"SOUTH"},
    }
    report["passed"] = report["passed"] and all(report["query_assertions"].values())
    report["warnings"].append(
        "This concentrated fixture tests matching groups, not production distributions. "
        "Negative/null cases and the target SQL engine require separate tests."
    )
    if not report["passed"]:
        raise ValueError(f"Query fixture failed coverage checks: {report}")
    manifest = build_generation_manifest(
        dataset_name="query_fixture",
        tables=data,
        seed=seed,
        parameters={
            "tables": TABLES,
            "query_profile": PROFILE,
            "sql": SQL,
            "python": sys.version,
            "date_context": date.today().isoformat(),
            "packages": {p: version(p) for p in ("great-generator", "pandas", "numpy", "faker")},
        },
        validation=report,
    )
    return data, result, manifest


if __name__ == "__main__":
    _, result, manifest = build_fixture()
    print(result.to_string(index=False))
    print(json.dumps(manifest, indent=2, default=str))
