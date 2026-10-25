"""Offline evidence for the skill helpers/examples; not a claim of agent behavior certification."""

from __future__ import annotations

import json
import runpy
import shutil
from pathlib import Path

import pandas as pd
import pytest

from great_generator import parse_ddl

ROOT = Path(__file__).resolve().parents[1]


def load(skill, file):
    return runpy.run_path(str(ROOT / "skills" / skill / file))


def test_skill_structure_links_and_public_imports():
    validator = runpy.run_path(str(ROOT / "scripts/validate_skills.py"))
    assert validator["validate"]() == []


def test_six_skills_have_actionable_evaluation_cases():
    suite = json.loads((ROOT / "skills/evaluations/cases.json").read_text(encoding="utf-8"))
    names = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
    assert {case["skill"] for case in suite} == names
    assert len({case["id"] for case in suite}) == len(suite)
    for case in suite:
        assert case["prompt"] and case["expected"] and case["must_not"]


@pytest.mark.parametrize(
    "skill,file,function",
    [
        ("schema-test-data", "schema_fixture.py", "build_fixture"),
        ("relational-test-fixtures", "customer_orders.py", "build_fixture"),
        ("query-test-data", "query_fixture.py", "build_fixture"),
        ("data-pipeline-test-pack", "pipeline_pack.py", "build_pack"),
    ],
)
def test_local_examples_execute_and_repeat(skill, file, function, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    build = load(skill, "examples/" + file)[function]
    first, *_, manifest = build(seed=42)
    second = build(seed=42)[0]
    if isinstance(first, dict):
        for name in first:
            pd.testing.assert_frame_equal(first[name], second[name])
    else:
        pd.testing.assert_frame_equal(first, second)
    assert manifest["validation"]["passed"]
    assert manifest["seed"] == 42 and not manifest["real_data_ingested"]
    json.dumps(manifest, default=str)
    assert list(tmp_path.iterdir()) == [], "Examples should return data, not silently export."


def test_individually_copied_skill_has_no_sibling_dependency(tmp_path):
    source = ROOT / "skills/relational-test-fixtures"
    destination = tmp_path / source.name
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__"))
    result = runpy.run_path(str(destination / "examples/customer_orders.py"))["build_fixture"]()
    assert result[1]["validation"]["passed"]


def test_key_checks_accept_repeated_fks_but_detect_nulls_orphans_and_duplicate_pks():
    check = load("relational-test-fixtures", "scripts/check_keys.py")["check_keys"]
    tables = {
        "parent": pd.DataFrame({"id": [1, 2]}),
        "child": pd.DataFrame({"id": [1, 2, 3], "parent_id": [1, 1, None]}),
    }
    options = {
        "primary_keys": {"parent": "id", "child": "id"},
        "relationships": [("child", "parent_id", "parent", "id")],
    }
    assert check(tables, **options)["passed"]
    assert not check(tables, **options, non_nullable=[("child", "parent_id")])["passed"]
    tables["child"].loc[2, "parent_id"] = 999
    assert not check(tables, **options)["passed"]
    tables["child"]["parent_id"] = 1
    tables["parent"].loc[1, "id"] = 1
    assert not check(tables, **options)["passed"]
    with pytest.raises(ValueError, match="Missing"):
        check(tables, primary_keys={"missing": "id"})
    assert not check(tables, primary_keys={})["passed"]


def test_query_example_checks_joined_groups_not_just_values():
    data, result, manifest = load("query-test-data", "examples/query_fixture.py")["build_fixture"]()
    report = manifest["validation"]
    assert report["passed"] and all(report["query_assertions"].values())
    assert set(result.product_type) == {"CHECKING", "SAVINGS"}
    counts = data["fact_transactions"].business_date.value_counts()
    assert len(counts) == 15 and counts.max() - counts.min() <= 1
    assert set(report) >= {"selectivity_actuals", "selectivity_targets", "join_coverage_status"}


def test_pipeline_anomalies_opt_in_and_expected_failures_are_observable():
    build = load("data-pipeline-test-pack", "examples/pipeline_pack.py")["build_pack"]
    normal, _ = build()
    dirty, manifest = build(include_anomalies=True)
    assert "deliberately_invalid" not in normal
    bad = dirty["deliberately_invalid"]
    assert not bad.customer_name.notna().all()
    assert not bad.balance.ge(0).all()
    assert not bad.customer_id.is_unique
    pd.testing.assert_frame_equal(normal["happy"], dirty["happy"])
    assert manifest["validation"]["scenarios"]["explicit_anomalies"]["expected_validation_failures"]


def test_history_checker_rejects_overlap_extra_current_and_null_key():
    check = load("data-pipeline-test-pack", "scripts/check_history.py")["check_history"]
    frame = pd.DataFrame(
        {
            "id": [1, 1],
            "scd_id": [1, 2],
            "effective_from": ["2026-01-01", "2026-02-01"],
            "effective_to": ["2026-02-01", "2026-03-01"],
            "is_current": [False, True],
        }
    )
    assert check(frame, "id")["passed"]
    overlap = frame.copy()
    overlap.loc[0, "effective_to"] = "2026-02-02"
    assert not check(overlap, "id")["passed"]
    two_current = frame.copy()
    two_current["is_current"] = True
    assert not check(two_current, "id")["passed"]
    frame.loc[0, "id"] = None
    assert not check(frame, "id")["passed"]
    assert not check(frame.head(0), "id")["passed"]


def test_contract_diff_tracks_fields_and_transitive_dependents():
    module = load("schema-change-regression", "examples/schema_diff.py")
    result = module["build_report"]()
    assert result["changed"]
    assert result["affected_fixtures"] == ["account", "customer", "txn"]
    assert any(c["kind"] == "TYPE_CHANGED" and c["impact"] == "high" for c in result["changes"])
    compare = load("schema-change-regression", "scripts/compare_contracts.py")["compare_contracts"]
    same = compare(parse_ddl(module["OLD"]), parse_ddl(module["OLD"]))
    assert not same["changed"] and not same["affected_fixtures"]


def test_contract_diff_retains_removed_edges_and_defaults():
    compare = load("schema-change-regression", "scripts/compare_contracts.py")["compare_contracts"]
    old = parse_ddl(
        "CREATE TABLE p (id INT PRIMARY KEY, value INT DEFAULT 1); "
        "CREATE TABLE c (id INT PRIMARY KEY, pid INT REFERENCES p(id));"
    )
    new = parse_ddl(
        "CREATE TABLE p (id INT PRIMARY KEY, value INT NOT NULL DEFAULT 2, x INT); "
        "CREATE TABLE c (id INT PRIMARY KEY, pid INT);"
    )
    result = compare(old, new)
    kinds = {c["kind"] for c in result["changes"]}
    assert {"FK_CHANGED", "DEFAULT_CHANGED", "COLUMN_ADDED", "NULLABILITY_CHANGED"} <= kinds
    assert result["affected_fixtures"] == ["c", "p"]
    removed = compare(old, parse_ddl("CREATE TABLE c (id INT PRIMARY KEY, pid INT);"))
    assert removed["removed_tables"] == ["p"] and "p" not in removed["regenerable_tables"]


def test_cdc_case_is_unique_and_has_consistent_before_after_preconditions():
    module = load("databricks-test-data", "examples/cdc_merge.py")
    initial, source, expected = module["build_case"]()
    assert source.customer_id.is_unique and source.customer_id.notna().all()
    assert set(source.operation) == {"insert", "update", "delete"}
    inserts = set(source.loc[source.operation == "insert", "customer_id"])
    deletes = set(source.loc[source.operation == "delete", "customer_id"])
    updates = set(source.loc[source.operation == "update", "customer_id"])
    assert not inserts.intersection(initial.customer_id)
    assert deletes.union(updates) <= set(initial.customer_id)
    assert set(expected.customer_id) == (set(initial.customer_id) - deletes) | inserts
    state = initial.set_index("customer_id").status.to_dict()
    for row in source.itertuples(index=False):
        if row.operation == "delete":
            del state[row.customer_id]
        else:
            state[row.customer_id] = row.status
    assert state == expected.set_index("customer_id").status.to_dict()


def test_cdc_case_rejects_ambiguous_order_and_bad_payload():
    module = load("databricks-test-data", "examples/cdc_merge.py")
    events = module["generate_cdc"]("banking", "customers", rows=8, operations=["insert"], seed=42)
    ambiguous = events.copy()
    ambiguous["sequence_number"] = 1
    with pytest.raises(ValueError, match="Ambiguous"):
        module["prepare_merge_case"](ambiguous)
    events["after"] = '{"customer_id": -1, "status": "active"}'
    with pytest.raises(ValueError, match="payload key"):
        module["prepare_merge_case"](events)


class RecordingFrame:
    columns = ["id", "event_date"]

    def __init__(self):
        self.calls = []

    @property
    def write(self):
        self.calls.append(("write",))
        return self

    def format(self, value):
        self.calls.append(("format", value))
        return self

    def mode(self, value):
        self.calls.append(("mode", value))
        return self

    def partitionBy(self, *columns):
        self.calls.append(("partitionBy", *columns))
        return self

    def saveAsTable(self, target):
        self.calls.append(("saveAsTable", target))

    def save(self, target):
        self.calls.append(("save", target))


def test_delta_writer_requires_exact_target_approval_and_defaults_to_error():
    write = load("databricks-test-data", "scripts/safe_delta.py")["write_delta"]
    frame = RecordingFrame()
    target = "sandbox.qa.fixture"
    with pytest.raises(ValueError, match="approval"):
        write(frame, target)
    with pytest.raises(ValueError, match="Overwrite"):
        write(frame, target, approved_target=target, mode="overwrite")
    with pytest.raises(ValueError, match="partition_by"):
        write(frame, target, approved_target=target, partition_by=["missing"])
    assert not frame.calls, "Safety errors must happen before requesting a writer."
    result = write(frame, target, approved_target=target, partition_by=["event_date"])
    assert result["mode"] == "errorifexists"
    assert ("mode", "errorifexists") in frame.calls
    assert frame.calls[-1] == ("saveAsTable", target)


@pytest.mark.parametrize(
    "target",
    [
        "s3://bucket/test/run1",
        "abfss://qa@account.dfs.core.windows.net/test/run1",
        "gs://bucket/test/run1",
        "dbfs:/tmp/gg/run1",
        "/Volumes/sandbox/qa/fixtures/run1",
    ],
)
def test_delta_path_writer_is_explicit_and_does_not_register_table(target):
    write = load("databricks-test-data", "scripts/safe_delta.py")["write_delta"]
    frame = RecordingFrame()
    write(frame, target, kind="path", approved_target=target)
    assert frame.calls[-1] == ("save", target)
    assert not any(call[0] == "saveAsTable" for call in frame.calls)


@pytest.mark.parametrize(
    "target,kind",
    [
        ("customers", "table"),
        ("sandbox.qa.x;DROP TABLE t", "table"),
        ("s3://bucket", "path"),
        ("s3://bucket/../x", "path"),
        ("https://example.com/file", "path"),
        ("", "path"),
    ],
)
def test_delta_target_validation_rejects_ambiguous_or_unsafe_targets(target, kind):
    validate = load("databricks-test-data", "scripts/safe_delta.py")["validate_target"]
    with pytest.raises(ValueError):
        validate(target, kind)
