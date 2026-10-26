import json

import pandas as pd
import pytest

from great_generator import compile_test_dataset, parse_ddl, parse_sql_workload
from great_generator.schemas.models import ColumnSpec, DomainSchema, TableSchema
from great_generator.testing import UnsatisfiableScenarioError

TABLES = {
    "dim_customer": {
        "schema": "customer_id int primary key, region string not null",
        "rows": 30,
    },
    "fact_orders": {
        "schema": (
            "order_id int primary key, "
            "customer_id int references dim_customer.customer_id, "
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


def test_sql_workload_parser_resolves_aliases_predicates_joins_and_aggregates():
    contract = parse_sql_workload(
        QUERY,
        schema={
            "dim_customer": ["customer_id", "region"],
            "fact_orders": [
                "order_id",
                "customer_id",
                "order_status",
                "order_date",
                "amount",
            ],
        },
    )

    query = contract.queries[0]
    assert query.tables == ("fact_orders", "dim_customer")
    assert query.joins[0].left.qualified_name == "fact_orders.customer_id"
    assert query.joins[0].right.qualified_name == "dim_customer.customer_id"
    assert [item.operator for item in query.predicates] == ["=", "=", ">="]
    assert query.predicates[2].values[0].isoformat() == "2026-01-01"
    assert query.group_by[0].qualified_name == "dim_customer.region"
    assert query.aggregates[0].function == "COUNT"
    assert query.supported is True


def test_sql_workload_parser_reads_files_and_reports_partial_boolean_support(tmp_path):
    path = tmp_path / "customer_filter.sql"
    path.write_text(
        "SELECT * FROM dim_customer WHERE region = 'EAST' OR NOT region = 'WEST'",
        encoding="utf-8",
    )

    contract = parse_sql_workload(
        path,
        schema={"dim_customer": ["customer_id", "region"]},
    )

    assert contract.source_files == (str(path),)
    assert contract.queries[0].query_id == "customer_filter"
    assert contract.queries[0].is_conjunctive is False
    assert any(item.code == "boolean_planning_partial" for item in contract.queries[0].diagnostics)


def test_sql_workload_parser_reports_ambiguous_and_unsupported_expressions():
    contract = parse_sql_workload(
        "SELECT id FROM left_table l JOIN right_table r ON l.id = r.id WHERE l.name LIKE 'A%'",
        schema={"left_table": ["id", "name"], "right_table": ["id"]},
    )
    diagnostics = contract.queries[0].diagnostics

    assert any(item.code == "ambiguous_column" for item in diagnostics)
    assert any(item.code == "unsupported_predicate" for item in diagnostics)
    assert contract.queries[0].supported is False


def test_compile_test_dataset_is_deterministic_and_preserves_relations():
    first = compile_test_dataset(TABLES, QUERY, seed=42)
    second = compile_test_dataset(TABLES, QUERY, seed=42)

    for table_name in first.datasets:
        pd.testing.assert_frame_equal(first.datasets[table_name], second.datasets[table_name])
    assert first.validation_report["passed"] is True
    assert (
        first.datasets["fact_orders"]["customer_id"]
        .isin(first.datasets["dim_customer"]["customer_id"])
        .all()
    )
    assert [item.to_dict() for item in first.scenarios] == [
        item.to_dict() for item in second.scenarios
    ]


def test_compile_test_dataset_reports_explicit_coverage_denominators():
    result = compile_test_dataset(
        TABLES,
        QUERY,
        coverage=["predicates", "joins", "boundaries"],
        seed=7,
    )
    report = result.coverage_report()

    assert report["predicate_coverage"] == {
        "covered": 6,
        "total": 6,
        "percentage": 100.0,
    }
    assert report["join_path_coverage"] == {
        "covered": 1,
        "total": 1,
        "percentage": 100.0,
    }
    assert report["boundary_coverage"] == {
        "covered": 1,
        "total": 1,
        "percentage": 100.0,
    }
    assert report["coverage_scope"] == "documented Phase 1 SQL subset"


def test_nullable_predicate_generates_unknown_sql_state():
    tables = {
        "events": {
            "schema": "event_id int primary key, category string, score double",
            "rows": 20,
        }
    }
    result = compile_test_dataset(
        tables,
        "SELECT * FROM events WHERE score >= 10",
        coverage=["predicates", "null_handling"],
        seed=2,
    )

    unknown = [item for item in result.scenarios if item.kind == "predicate_unknown"]
    assert len(unknown) == 1
    assert unknown[0].expected_query_outcome == "UNKNOWN"
    assert result.coverage_report()["predicate_coverage"]["total"] == 3


def test_schema_constraint_conflict_fails_with_actionable_error():
    schema = DomainSchema(
        name="status_contract",
        description="Constraint conflict fixture",
        tables={
            "orders": TableSchema(
                name="orders",
                columns=(
                    ColumnSpec("order_id", "int", nullable=False),
                    ColumnSpec(
                        "order_status",
                        "string",
                        nullable=False,
                        accepted_values=("OPEN", "CLOSED"),
                    ),
                ),
                primary_key="order_id",
            )
        },
    )

    with pytest.raises(UnsatisfiableScenarioError, match="schema_allowed_values"):
        compile_test_dataset(
            schema,
            "SELECT * FROM orders WHERE order_status = 'COMPLETED'",
            rows=20,
        )


def test_insufficient_rows_for_witnesses_fails_clearly():
    tables = {table: spec["schema"] for table, spec in TABLES.items()}
    with pytest.raises(ValueError, match="cannot hold distinct coverage witnesses"):
        compile_test_dataset(tables, QUERY, rows=2, seed=1)


def test_negative_cases_are_labeled_and_separate_from_clean_baseline():
    result = compile_test_dataset(
        TABLES,
        QUERY,
        coverage=["predicates", "joins", "negative_cases"],
        seed=4,
    )

    assert set(result.negative_datasets) == {"missing_foreign_key", "unexpected_null"}
    assert result.validation_report["passed"] is True
    assert result.coverage_report()["negative_case_coverage"] == {
        "covered": 2,
        "total": 2,
        "percentage": 100.0,
    }
    clean_keys = set(result.datasets["dim_customer"]["customer_id"])
    assert result.datasets["fact_orders"]["customer_id"].isin(clean_keys).all()
    assert (
        not result.negative_datasets["missing_foreign_key"]["fact_orders"]["customer_id"]
        .isin(clean_keys)
        .all()
    )


def test_expected_results_are_bounded_reference_evaluator_assertions():
    result = compile_test_dataset(TABLES, QUERY, seed=8)

    assert result.expected_results
    assert all(item["verified"] for item in result.expected_results)
    assert {item["expected"] for item in result.expected_results}.issuperset({"TRUE", "FALSE"})
    assert all(
        item["derivation"] == "independent three-valued predicate evaluator"
        for item in result.expected_results
    )


def test_export_writes_data_contract_reports_and_static_html(tmp_path):
    result = compile_test_dataset(TABLES, QUERY, seed=9)
    root = result.export(tmp_path / "compiled", format="csv")
    html_report = result.generate_report(format="html", output=root / "coverage_report.html")

    assert (root / "datasets" / "fact_orders.csv").exists()
    assert (root / "query_contract.json").exists()
    assert (root / "coverage_report.json").exists()
    assert (root / "generation_manifest.json").exists()
    assert html_report.exists()
    payload = json.loads((root / "generation_manifest.json").read_text(encoding="utf-8"))
    assert payload["synthetic"] is True
    assert payload["source_data_read"] is False
    assert payload["generation"]["schema_contract_hash"].startswith("sha256:")


def test_compile_accepts_sql_ddl_contract():
    contract = parse_ddl("""
        CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, region VARCHAR(20));
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            status VARCHAR(20),
            CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id)
              REFERENCES customers(customer_id)
        );
        """)
    result = compile_test_dataset(
        contract,
        "SELECT * FROM orders o JOIN customers c ON o.customer_id = c.customer_id "
        "WHERE c.region = 'EAST' AND o.status = 'COMPLETE'",
        rows={"customers": 20, "orders": 30},
        seed=10,
    )

    assert result.validation_report["passed"] is True


def test_compile_rejects_spark_without_driver_side_fallback():
    with pytest.raises(NotImplementedError, match="does not fall back"):
        compile_test_dataset(TABLES, QUERY, engine="spark", seed=1)


def test_generated_witness_detects_a_missing_filter_mutation():
    result = compile_test_dataset(
        TABLES,
        QUERY,
        coverage=["predicates", "joins"],
        seed=12,
    )
    joined = result.datasets["fact_orders"].merge(
        result.datasets["dim_customer"], on="customer_id", how="inner"
    )
    correct = joined[
        (joined["region"] == "EAST")
        & (joined["order_status"] == "COMPLETED")
        & (joined["order_date"].map(str) >= "2026-01-01")
    ]
    missing_status_filter = joined[
        (joined["region"] == "EAST") & (joined["order_date"].map(str) >= "2026-01-01")
    ]

    assert len(missing_status_filter) > len(correct)


def test_existing_generation_api_is_unchanged_without_contract_compiler():
    from great_generator import generate_relational

    first = generate_relational(TABLES, seed=99)
    second = generate_relational(TABLES, seed=99)
    for table_name in first:
        pd.testing.assert_frame_equal(first[table_name], second[table_name])
