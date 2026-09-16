"""Schema-source ingestion examples for Great Generator.

Run with:
    python examples/07-schema-source-ingestion.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from great_generator import (
    generate_from_data_dictionary,
    generate_from_dbt_manifest,
    generate_from_dbt_schema,
    generate_from_json_schema,
)

json_schema = {
    "type": "object",
    "required": ["customer_id", "email"],
    "properties": {
        "customer_id": {"type": "integer"},
        "email": {"type": "string", "format": "email"},
        "status": {"type": "string", "enum": ["ACTIVE", "INACTIVE", "PENDING"]},
        "balance": {"type": "number", "minimum": 0, "maximum": 10000},
    },
}


def main() -> None:
    print("JSON Schema")
    print(generate_from_json_schema(json_schema, rows=5).head())

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)

        schema_yml = root / "schema.yml"
        schema_yml.write_text(
            """
version: 2
models:
  - name: customers
    columns:
      - name: customer_id
        data_type: integer
        tests: [unique, not_null]
      - name: email
        data_type: string
      - name: status
        data_type: string
        tests:
          - accepted_values:
              values: [ACTIVE, INACTIVE, PENDING]
""".strip(),
            encoding="utf-8",
        )
        print("\ndbt schema.yml")
        print(generate_from_dbt_schema(schema_yml, model_name="customers", rows=5).head())

        manifest = root / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "nodes": {
                        "model.demo.customers": {
                            "resource_type": "model",
                            "name": "customers",
                            "columns": {
                                "customer_id": {
                                    "name": "customer_id",
                                    "data_type": "integer",
                                    "tests": ["unique", "not_null"],
                                },
                                "status": {
                                    "name": "status",
                                    "data_type": "string",
                                    "tests": [
                                        {"accepted_values": {"values": ["ACTIVE", "INACTIVE"]}}
                                    ],
                                },
                            },
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        print("\ndbt manifest.json")
        print(generate_from_dbt_manifest(manifest, model_name="customers", rows=5).head())

        dictionary = root / "data_dictionary.csv"
        dictionary.write_text(
            """column_name,data_type,nullable,allowed_values,min,max,unique
customer_id,integer,false,,,,true
email,string,false,,,,true
status,string,false,ACTIVE|INACTIVE|PENDING,,,
balance,decimal,true,,0,10000,
""",
            encoding="utf-8",
        )
        print("\nData dictionary")
        print(generate_from_data_dictionary(dictionary, rows=5).head())


if __name__ == "__main__":
    main()
