"""Small, local-only schema fixture. Run from a source checkout after pip install -e ."""

from __future__ import annotations

import json
import sys
from datetime import date
from importlib.metadata import version

from great_generator import generate_from_json_schema, validate_generated_data
from great_generator.io.manifest import build_generation_manifest

SCHEMA = {
    "type": "object",
    "required": ["customer_id", "email", "status", "balance"],
    "properties": {
        "customer_id": {"type": "integer"},
        "email": {"type": "string", "format": "email"},
        "status": {"type": "string", "enum": ["ACTIVE", "INACTIVE"]},
        "balance": {"type": "number", "minimum": 0, "maximum": 10000},
    },
}


def build_fixture(rows=24, seed=42):
    """Return a DataFrame plus provenance; do not write or upload anything."""
    df = generate_from_json_schema(SCHEMA, rows=rows, seed=seed)
    # Run after ingestion post-processing; semantic checks are not full contract validation.
    semantic = validate_generated_data(df)
    checks = {
        "rows": len(df) == rows,
        "required_non_null": not df[list(SCHEMA["required"])].isna().any().any(),
        "key_unique": df.customer_id.is_unique,
        "categories": df.status.isin(["ACTIVE", "INACTIVE"]).all(),
        "bounds": df.balance.between(0, 10000).all(),
        "email_shape": df.email.str.contains(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", regex=True).all(),
    }
    checks = {name: bool(value) for name, value in checks.items()}
    manifest = build_generation_manifest(
        dataset_name="schema_fixture",
        tables={"customers": df},
        seed=seed,
        parameters={
            "schema": SCHEMA,
            "rows": rows,
            "python": sys.version,
            "date_context": date.today().isoformat(),
            "packages": {p: version(p) for p in ("great-generator", "pandas", "numpy", "faker")},
        },
        validation={"passed": all(checks.values()), "checks": checks, "semantic": semantic},
        warnings=["Email shape is checked; deliverability is not."],
    )
    if not all(checks.values()):
        raise ValueError(f"Fixture failed explicit checks: {checks}")
    return df, manifest


if __name__ == "__main__":
    _, manifest = build_fixture()
    print(json.dumps(manifest, indent=2, default=str))
