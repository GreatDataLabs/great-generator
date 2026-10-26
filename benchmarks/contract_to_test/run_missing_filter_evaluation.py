"""Reproducible local comparison for one controlled missing-filter defect."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from great_generator import __version__, compile_test_dataset, generate_relational

TABLES = {
    "dim_customer": {
        "schema": "customer_id int primary key, region string not null",
        "rows": 30,
    },
    "fact_orders": {
        "schema": (
            "order_id int primary key, customer_id int references dim_customer.customer_id, "
            "order_status string not null, order_date date not null, amount double"
        ),
        "rows": 60,
    },
}
QUERY = """
SELECT c.region, COUNT(*) AS order_count
FROM fact_orders f
JOIN dim_customer c ON f.customer_id = c.customer_id
WHERE c.region = 'EAST'
  AND f.order_status = 'COMPLETED'
  AND f.order_date >= DATE '2026-01-01'
GROUP BY c.region
"""
SEED = 12


def run_evaluation() -> dict[str, Any]:
    """Execute three generation strategies against the same controlled defect."""

    results: dict[str, Any] = {}
    started = time.perf_counter()
    schema_only = generate_relational(TABLES, seed=SEED)
    results["schema_only"] = _measure(schema_only, time.perf_counter() - started)

    started = time.perf_counter()
    query_aware = generate_relational(
        TABLES,
        required_values={
            "dim_customer.region": ["EAST"],
            "fact_orders.order_status": ["COMPLETED"],
        },
        # The existing query-aware API injects values but does not compile SQL witness rows.
        # Join coverage is omitted because fact_orders has no inbound child relationship.
        ensure_join_coverage=False,
        seed=SEED,
    )
    results["query_aware"] = _measure(query_aware, time.perf_counter() - started)

    started = time.perf_counter()
    compiled = compile_test_dataset(
        TABLES,
        QUERY,
        coverage=["predicates", "joins", "boundaries"],
        seed=SEED,
    )
    contract_measurement = _measure(compiled.datasets, time.perf_counter() - started)
    contract_measurement["coverage"] = compiled.coverage_report()
    results["contract_to_test"] = contract_measurement

    return {
        "project": "great-generator",
        "benchmark_version": "1",
        "great_generator_version": __version__,
        "git_commit": _git_commit(),
        "synthetic": True,
        "measured": True,
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "methodology": "benchmarks/methodology/benchmark_protocol.md",
        "experiment": "controlled missing order_status filter",
        "query_hash": _hash(QUERY),
        "schema_hash": _hash(TABLES),
        "seed": SEED,
        "repetitions": 1,
        "environment": {
            "python_version": platform.python_version(),
            "pandas_version": pd.__version__,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "logical_cpu_count": os.cpu_count(),
            "physical_memory_bytes": _physical_memory_bytes(),
            "execution_engine": "pandas",
        },
        "results": results,
        "limitations": [
            "This is one local deterministic fixture, not a general performance benchmark.",
            "Mutation detection is measured by a row-count difference between the reference "
            "filter and a controlled missing-filter mutant.",
            "Durations are informative for this run only and are not cross-platform claims.",
        ],
    }


def _measure(data: dict[str, pd.DataFrame], generation_seconds: float) -> dict[str, Any]:
    started = time.perf_counter()
    joined = data["fact_orders"].merge(data["dim_customer"], on="customer_id", how="inner")
    correct = joined[
        (joined["region"] == "EAST")
        & (joined["order_status"] == "COMPLETED")
        & (joined["order_date"].map(str) >= "2026-01-01")
    ]
    mutant = joined[(joined["region"] == "EAST") & (joined["order_date"].map(str) >= "2026-01-01")]
    execution_seconds = time.perf_counter() - started
    return {
        "rows": {name: len(frame) for name, frame in data.items()},
        "reference_row_count": len(correct),
        "mutant_row_count": len(mutant),
        "defect_detected": len(correct) != len(mutant),
        "generation_seconds": generation_seconds,
        "execution_seconds": execution_seconds,
    }


def _hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, default=str).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _git_commit() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _physical_memory_bytes() -> int | None:
    """Return detected physical memory without adding a benchmark dependency."""

    if os.name == "nt":

        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong),
                ("memory_load", ctypes.c_ulong),
                ("total_physical", ctypes.c_ulonglong),
                ("available_physical", ctypes.c_ulonglong),
                ("total_page_file", ctypes.c_ulonglong),
                ("available_page_file", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong),
                ("available_virtual", ctypes.c_ulonglong),
                ("available_extended_virtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.length = ctypes.sizeof(MemoryStatus)
        try:
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.total_physical)
        except (AttributeError, OSError):
            return None
        return None
    try:
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        pages = int(os.sysconf("SC_PHYS_PAGES"))
    except (AttributeError, OSError, TypeError, ValueError):
        return None
    return page_size * pages


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_evaluation()
    text = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
