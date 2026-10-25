"""Read-only schema-change report. Regeneration is a separate user decision."""

from __future__ import annotations

import json
import runpy
from pathlib import Path

from great_generator import parse_ddl

OLD = """
CREATE TABLE customer (customer_id INT PRIMARY KEY, email VARCHAR(100));
CREATE TABLE account (account_id INT PRIMARY KEY,
    customer_id INT REFERENCES customer(customer_id));
CREATE TABLE txn (txn_id INT PRIMARY KEY, account_id INT REFERENCES account(account_id));
"""
NEW = OLD.replace("customer_id INT", "customer_id BIGINT").replace("VARCHAR(100)", "VARCHAR(255)")


def build_report():
    compare = runpy.run_path(str(Path(__file__).parents[1] / "scripts/compare_contracts.py"))[
        "compare_contracts"
    ]
    return compare(parse_ddl(OLD), parse_ddl(NEW))


if __name__ == "__main__":
    print(json.dumps(build_report(), indent=2))
