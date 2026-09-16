import pandas as pd
import pytest

from great_generator import (
    generate_from_schema,
    generate_relational,
    validate_query_coverage,
)

SINGLE_TABLE_SCHEMA = """
member_id string,
business_date date,
region string,
product_type string,
member_status string,
interaction_count int,
balance double
"""


RELATIONAL_TABLES = {
    "dim_member": {
        "schema": "member_id int primary key, region string, member_status string",
        "rows": 12,
    },
    "dim_product": {
        "schema": "product_id int primary key, product_type string",
        "rows": 6,
    },
    "fact_interaction": {
        "schema": (
            "interaction_id int primary key, "
            "member_id int references dim_member.member_id, "
            "product_id int references dim_product.product_id, "
            "business_date date, interaction_count int"
        ),
        "rows": 60,
    },
}

RELATIONSHIPS = [
    "fact_interaction.member_id -> dim_member.member_id",
    "fact_interaction.product_id -> dim_product.product_id",
]


def test_generate_from_schema_unchanged_without_query_aware_arguments():
    baseline = generate_from_schema(SINGLE_TABLE_SCHEMA, rows=25, seed=123)
    repeated = generate_from_schema(SINGLE_TABLE_SCHEMA, rows=25, seed=123)

    pd.testing.assert_frame_equal(baseline, repeated)


def test_required_values_appear_without_eliminating_other_values():
    df = generate_from_schema(
        SINGLE_TABLE_SCHEMA,
        rows=100,
        required_values={
            "region": ["SOUTH"],
            "product_type": ["CHECKING", "SAVINGS"],
            "member_status": ["ACTIVE"],
        },
        seed=42,
    )

    assert "SOUTH" in set(df["region"])
    assert {"CHECKING", "SAVINGS"}.issubset(set(df["product_type"]))
    assert "ACTIVE" in set(df["member_status"])
    assert len(set(df["region"])) > 1
    assert len(set(df["product_type"])) > 2


def test_target_selectivity_is_approximately_satisfied():
    df = generate_from_schema(
        SINGLE_TABLE_SCHEMA,
        rows=200,
        target_selectivity={
            "region": {"SOUTH": 0.25},
            "product_type": {"CHECKING": 0.30, "SAVINGS": 0.20},
        },
        seed=42,
    )

    south_ratio = (df["region"] == "SOUTH").mean()
    checking_ratio = (df["product_type"] == "CHECKING").mean()
    savings_ratio = (df["product_type"] == "SAVINGS").mean()

    assert 0.22 <= south_ratio <= 0.28
    assert 0.27 <= checking_ratio <= 0.33
    assert 0.17 <= savings_ratio <= 0.23


def test_partition_by_balanced_values_are_generated():
    df = generate_from_schema(
        SINGLE_TABLE_SCHEMA,
        rows=101,
        partition_by={
            "column": "business_date",
            "values": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "distribution": "balanced",
        },
        seed=42,
    )

    counts = df["business_date"].map(str).value_counts()

    assert set(counts.index) == {"2026-01-01", "2026-01-02", "2026-01-03"}
    assert counts.max() - counts.min() <= 1


def test_partition_by_custom_counts_are_generated():
    df = generate_from_schema(
        SINGLE_TABLE_SCHEMA,
        rows=6,
        partition_by={
            "column": "business_date",
            "counts": {
                "2026-01-01": 2,
                "2026-01-02": 4,
            },
        },
        seed=42,
    )

    assert df["business_date"].map(str).value_counts().to_dict() == {
        "2026-01-02": 4,
        "2026-01-01": 2,
    }


def test_partition_by_custom_counts_must_match_rows():
    with pytest.raises(ValueError, match="custom counts must sum to rows"):
        generate_from_schema(
            SINGLE_TABLE_SCHEMA,
            rows=5,
            partition_by={
                "column": "business_date",
                "counts": {"2026-01-01": 2, "2026-01-02": 4},
            },
            seed=42,
        )


def test_invalid_required_partition_and_selectivity_raise_clear_errors():
    with pytest.raises(ValueError, match="unknown column 'missing'"):
        generate_from_schema(
            SINGLE_TABLE_SCHEMA,
            rows=10,
            required_values={"missing": ["SOUTH"]},
        )

    with pytest.raises(ValueError, match="unknown column 'missing'"):
        generate_from_schema(
            SINGLE_TABLE_SCHEMA,
            rows=10,
            partition_by={"column": "missing", "values": ["2026-01-01"]},
        )

    with pytest.raises(ValueError, match="between 0 and 1"):
        generate_from_schema(
            SINGLE_TABLE_SCHEMA,
            rows=10,
            target_selectivity={"region": {"SOUTH": 1.2}},
        )


def test_query_profile_is_supported_and_direct_arguments_override_it():
    df = generate_from_schema(
        SINGLE_TABLE_SCHEMA,
        rows=30,
        query_profile={
            "required_values": {"region": ["NORTH"]},
            "partition_by": {"column": "business_date", "values": ["2026-01-01"]},
        },
        required_values={"region": ["SOUTH"]},
        seed=42,
    )

    assert "SOUTH" in set(df["region"])
    assert "2026-01-01" in set(df["business_date"].map(str))


def test_seeded_query_aware_generation_is_deterministic():
    kwargs = {
        "rows": 80,
        "required_values": {"region": ["SOUTH"]},
        "partition_by": {
            "column": "business_date",
            "values": ["2026-01-01", "2026-01-02"],
        },
        "target_selectivity": {"region": {"SOUTH": 0.25}},
        "seed": 2026,
    }

    first = generate_from_schema(SINGLE_TABLE_SCHEMA, **kwargs)
    second = generate_from_schema(SINGLE_TABLE_SCHEMA, **kwargs)

    pd.testing.assert_frame_equal(first, second)


def test_generate_relational_unchanged_without_query_aware_arguments():
    baseline = generate_relational(tables=RELATIONAL_TABLES, seed=123)
    repeated = generate_relational(tables=RELATIONAL_TABLES, seed=123)

    for table_name in baseline:
        pd.testing.assert_frame_equal(baseline[table_name], repeated[table_name])


def test_relational_required_values_partitioning_and_join_coverage():
    data = generate_relational(
        tables=RELATIONAL_TABLES,
        required_values={
            "dim_member.region": ["SOUTH"],
            "dim_member.member_status": ["ACTIVE"],
            "dim_product.product_type": ["CHECKING", "SAVINGS"],
        },
        partition_by={
            "table": "fact_interaction",
            "column": "business_date",
            "values": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "distribution": "balanced",
        },
        ensure_join_coverage=True,
        seed=42,
    )

    assert "SOUTH" in set(data["dim_member"]["region"])
    assert "ACTIVE" in set(data["dim_member"]["member_status"])
    assert {"CHECKING", "SAVINGS"}.issubset(set(data["dim_product"]["product_type"]))
    assert set(data["fact_interaction"]["business_date"].map(str)) == {
        "2026-01-01",
        "2026-01-02",
        "2026-01-03",
    }

    members = data["dim_member"].query("region == 'SOUTH' and member_status == 'ACTIVE'")
    products = data["dim_product"][
        data["dim_product"]["product_type"].isin(["CHECKING", "SAVINGS"])
    ]
    facts = data["fact_interaction"]

    assert facts["member_id"].isin(members["member_id"]).any()
    assert facts["product_id"].isin(products["product_id"]).any()


def test_relational_invalid_table_qualified_column_raises():
    with pytest.raises(ValueError, match="unknown table 'missing'"):
        generate_relational(
            tables=RELATIONAL_TABLES,
            required_values={"missing.region": ["SOUTH"]},
        )


def test_relational_join_coverage_requires_relationship():
    with pytest.raises(ValueError, match="requires a child relationship"):
        generate_relational(
            tables={
                "dim_member": {
                    "schema": "member_id int primary key, region string",
                    "rows": 5,
                }
            },
            required_values={"dim_member.region": ["SOUTH"]},
            ensure_join_coverage=True,
        )


def test_relational_query_aware_generation_is_deterministic():
    kwargs = {
        "tables": RELATIONAL_TABLES,
        "required_values": {"dim_member.region": ["SOUTH"]},
        "partition_by": {
            "table": "fact_interaction",
            "column": "business_date",
            "values": ["2026-01-01", "2026-01-02"],
        },
        "ensure_join_coverage": True,
        "seed": 2026,
    }
    first = generate_relational(**kwargs)
    second = generate_relational(**kwargs)

    for table_name in first:
        pd.testing.assert_frame_equal(first[table_name], second[table_name])


def test_validate_query_coverage_reports_required_partition_selectivity_and_join_status():
    data = generate_relational(
        tables=RELATIONAL_TABLES,
        required_values={
            "dim_member.region": ["SOUTH"],
            "dim_product.product_type": ["CHECKING"],
        },
        partition_by={
            "table": "fact_interaction",
            "column": "business_date",
            "values": ["2026-01-01", "2026-01-02"],
        },
        ensure_join_coverage=True,
        seed=42,
    )

    report = validate_query_coverage(
        data=data,
        required_values={
            "dim_member.region": ["SOUTH"],
            "dim_product.product_type": ["CHECKING"],
        },
        partition_by={
            "table": "fact_interaction",
            "column": "business_date",
            "values": ["2026-01-01", "2026-01-02"],
        },
        target_selectivity={"dim_member.region": {"SOUTH": 0.25}},
        relationships=RELATIONSHIPS,
        ensure_join_coverage=True,
    )

    assert report["required_values_status"]["dim_member.region"]["SOUTH"] is True
    assert (
        report["partition_coverage_status"]["fact_interaction.business_date"]["2026-01-01"] is True
    )
    assert "fact_interaction.business_date" in report["partition_counts"]
    assert "dim_member.region" in report["selectivity_actuals"]
    assert report["join_coverage_status"]["fact_interaction->dim_member.region"] is True
    assert report["passed"] is True


def test_validate_query_coverage_warns_when_selectivity_is_not_close():
    df = generate_from_schema(
        SINGLE_TABLE_SCHEMA,
        rows=20,
        required_values={"region": ["SOUTH"]},
        seed=42,
    )

    report = validate_query_coverage(
        data=df,
        target_selectivity={"region": {"SOUTH": 0.90}},
    )

    assert report["warnings"]


# Acceptance-criteria friendly aliases for query-aware examples and coverage docs.


def test_required_values_present():
    df = generate_from_schema(
        SINGLE_TABLE_SCHEMA,
        rows=30,
        required_values={"region": ["SOUTH"], "product_type": ["CHECKING"]},
        seed=7,
    )

    assert "SOUTH" in set(df["region"])
    assert "CHECKING" in set(df["product_type"])


def test_partition_values_present():
    values = ["2026-01-01", "2026-01-02", "2026-01-03"]
    df = generate_from_schema(
        SINGLE_TABLE_SCHEMA,
        rows=30,
        partition_by={"column": "business_date", "values": values},
        seed=7,
    )

    assert set(df["business_date"].map(str)) == set(values)


def test_balanced_partition_counts():
    df = generate_from_schema(
        SINGLE_TABLE_SCHEMA,
        rows=30,
        partition_by={
            "column": "business_date",
            "values": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "distribution": "balanced",
        },
        seed=7,
    )

    counts = df["business_date"].map(str).value_counts()
    assert counts.max() - counts.min() == 0


def test_query_coverage_report():
    required_values = {"region": ["SOUTH"]}
    partition_by = {"column": "business_date", "values": ["2026-01-01"]}
    df = generate_from_schema(
        SINGLE_TABLE_SCHEMA,
        rows=25,
        required_values=required_values,
        partition_by=partition_by,
        seed=7,
    )

    report = validate_query_coverage(
        data=df,
        required_values=required_values,
        partition_by=partition_by,
        target_selectivity={"region": {"SOUTH": 0.20}},
    )

    assert set(report).issuperset(
        {
            "required_values_status",
            "partition_coverage_status",
            "partition_counts",
            "selectivity_actuals",
            "selectivity_targets",
            "join_coverage_status",
            "warnings",
        }
    )


def test_existing_behavior_unchanged_without_query_args():
    first = generate_from_schema(SINGLE_TABLE_SCHEMA, rows=20, seed=77)
    second = generate_from_schema(SINGLE_TABLE_SCHEMA, rows=20, seed=77)

    pd.testing.assert_frame_equal(first, second)
