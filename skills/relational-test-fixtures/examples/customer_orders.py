"""Generate and explicitly validate related fixtures, without exporting them."""

from __future__ import annotations

import json
import runpy
import sys
from datetime import date
from importlib.metadata import version
from pathlib import Path

from great_generator import generate_relational, parse_ddl
from great_generator.io.manifest import build_generation_manifest

DDL = """
CREATE TABLE customers (customer_id INT PRIMARY KEY, customer_name VARCHAR(100));
CREATE TABLE orders (
    order_id INT PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(customer_id),
    amount DOUBLE
);
"""


def build_fixture(seed=42):
    contract = parse_ddl(DDL)
    tables = {
        "customers": {"schema": contract.tables["customers"], "rows": 12},
        "orders": {"schema": contract.tables["orders"], "rows": 48},
    }
    # TableSchema specs do not currently carry FKs through this adapter; pass them explicitly.
    data = generate_relational(
        tables, relationships=["orders.customer_id -> customers.customer_id"], seed=seed
    )
    check = runpy.run_path(str(Path(__file__).parents[1] / "scripts/check_keys.py"))["check_keys"]
    validation = check(
        data,
        primary_keys={"customers": "customer_id", "orders": "order_id"},
        relationships=[("orders", "customer_id", "customers", "customer_id")],
        non_nullable=[("orders", "customer_id")],
    )
    validation["row_counts"] = {name: len(df) for name, df in data.items()}
    if not validation["passed"]:
        raise ValueError(f"Relational fixture failed validation: {validation}")
    manifest = build_generation_manifest(
        dataset_name="customer_orders",
        tables=data,
        seed=seed,
        schema_fingerprint=contract.fingerprint(),
        parameters={
            "python": sys.version,
            "date_context": date.today().isoformat(),
            "packages": {p: version(p) for p in ("great-generator", "pandas", "numpy", "faker")},
            "ddl": DDL,
            "rows": {name: spec["rows"] for name, spec in tables.items()},
            "relationships": ["orders.customer_id -> customers.customer_id"],
        },
        validation=validation,
    )
    return data, manifest


if __name__ == "__main__":
    _, manifest = build_fixture()
    print(json.dumps(manifest, indent=2, default=str))
