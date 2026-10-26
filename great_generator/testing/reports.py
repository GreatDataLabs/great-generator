"""Measured coverage and static reporting for contract-to-test results."""

from __future__ import annotations

import html
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from great_generator.schemas.models import DomainSchema
from great_generator.testing.constraint_planner import DEFAULT_COVERAGE
from great_generator.testing.query_contract import CoverageScenario, WorkloadContract


def build_coverage_report(
    *,
    workload: WorkloadContract,
    schema: DomainSchema,
    scenarios: Sequence[CoverageScenario],
    validation: Mapping[str, Any],
    coverage: Sequence[str] | None,
    planner_warnings: Sequence[str],
    negative_cases: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build coverage percentages from explicit, validated denominators."""

    requested = tuple(coverage or DEFAULT_COVERAGE)
    validated = {item["scenario_id"]: item for item in validation.get("scenarios", [])}
    covered_predicate_states: dict[str, set[str]] = {}
    for item in validation.get("scenarios", []):
        if not item.get("passed"):
            continue
        for requirement_id, state in item.get("predicate_states", {}).items():
            key = f"{item['query_id']}.{requirement_id}"
            covered_predicate_states.setdefault(key, set()).add(str(state))

    predicate_total = 0
    predicate_covered = 0
    predicate_details: dict[str, dict[str, Any]] = {}
    for query in workload.queries:
        for predicate in query.predicates:
            column = _column(schema, predicate.column.table, predicate.column.column)
            desired = {"TRUE", "FALSE"} if "predicates" in requested else set()
            if "null_handling" in requested and column.nullable:
                desired.add("UNKNOWN")
            detail_key = f"{query.query_id}.{predicate.requirement_id}"
            actual = covered_predicate_states.get(detail_key, set())
            predicate_total += len(desired)
            predicate_covered += len(desired & actual)
            predicate_details[detail_key] = {
                "expression": predicate.expression,
                "required_states": sorted(desired),
                "covered_states": sorted(desired & actual),
                "uncovered_states": sorted(desired - actual),
            }

    joins = [join for query in workload.queries for join in query.joins]
    join_total = len(joins) if "joins" in requested else 0
    join_covered_ids = {
        f"{item['query_id']}.{requirement_id}"
        for item in validation.get("scenarios", [])
        if item.get("passed")
        for requirement_id, status in item.get("join_status", {}).items()
        if status
    }
    join_covered = sum(
        f"{query.query_id}.{join.requirement_id}" in join_covered_ids
        for query in workload.queries
        for join in query.joins
    )

    boundary_targets = [
        predicate
        for query in workload.queries
        for predicate in query.predicates
        if predicate.operator in {">", ">=", "<", "<=", "BETWEEN", "NOT BETWEEN"}
    ]
    boundary_total = len(boundary_targets) if "boundaries" in requested else 0
    boundary_covered_ids = {
        f"{scenario.query_id}.{requirement}"
        for scenario in scenarios
        if scenario.kind.startswith("boundary_")
        and validated.get(scenario.scenario_id, {}).get("passed")
        for requirement in scenario.target_requirements
    }
    boundary_covered = sum(
        f"{query.query_id}.{predicate.requirement_id}" in boundary_covered_ids
        for query in workload.queries
        for predicate in query.predicates
        if predicate.operator in {">", ">=", "<", "<=", "BETWEEN", "NOT BETWEEN"}
    )

    negative_total = 2 if "negative_cases" in requested else 0
    negative_covered = len(negative_cases or {}) if negative_total else 0
    unsupported = [
        {
            "query_id": query.query_id,
            **diagnostic.to_dict(),
        }
        for query in workload.queries
        for diagnostic in query.diagnostics
    ]
    uncovered = [
        {
            "requirement": key,
            "states": details["uncovered_states"],
            "reason": "No validated witness was generated under the current schema constraints.",
        }
        for key, details in predicate_details.items()
        if details["uncovered_states"]
    ]
    warnings = list(dict.fromkeys([*planner_warnings, *validation_warnings(validation)]))
    return {
        "report_version": "1.0",
        "coverage_scope": "documented Phase 1 SQL subset",
        "requested_coverage": list(requested),
        "extracted_testable_requirements": {
            "predicates": sum(len(query.predicates) for query in workload.queries),
            "joins": len(joins),
            "boundaries": len(boundary_targets),
        },
        "supported_requirements": [
            requirement
            for query in workload.queries
            for requirement in [
                *(f"{query.query_id}.{predicate.requirement_id}" for predicate in query.predicates),
                *(f"{query.query_id}.{join.requirement_id}" for join in query.joins),
            ]
        ],
        "unsupported_requirements": unsupported,
        "scenarios_generated": len(scenarios),
        "scenarios_validated": len(validated),
        "scenarios_passed": sum(bool(item.get("passed")) for item in validated.values()),
        "predicate_coverage": _metric(predicate_covered, predicate_total),
        "predicate_details": predicate_details,
        "join_path_coverage": _metric(join_covered, join_total),
        "boundary_coverage": _metric(boundary_covered, boundary_total),
        "negative_case_coverage": _metric(negative_covered, negative_total),
        "uncovered_conditions": uncovered,
        "constraint_conflicts": [],
        "generation_warnings": warnings,
        "clean_dataset_validation_passed": bool(validation.get("passed")),
    }


def expected_result_assertions(
    validation: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Return bounded witness assertions derived by the reference evaluator."""

    return [
        {
            "query_id": item["query_id"],
            "scenario_id": item["scenario_id"],
            "assertion_type": "bounded_boolean_outcome",
            "expected": item["expected_query_outcome"],
            "observed": item["actual_query_outcome"],
            "verified": bool(item["passed"]),
            "derivation": "independent three-valued predicate evaluator",
        }
        for item in validation.get("scenarios", [])
    ]


def write_static_html_report(payload: Mapping[str, Any], path: str | Path) -> Path:
    """Write a dependency-free static report without embedding generated records."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    coverage = payload.get("coverage", {})
    validation = payload.get("validation", {})
    rows = "".join(
        f"<tr><th>{html.escape(label)}</th><td>{html.escape(str(value.get('covered', 0)))}</td>"
        f"<td>{html.escape(str(value.get('total', 0)))}</td>"
        f"<td>{html.escape(str(value.get('percentage')))}</td></tr>"
        for label, value in (
            ("Predicate states", coverage.get("predicate_coverage", {})),
            ("Join paths", coverage.get("join_path_coverage", {})),
            ("Boundaries", coverage.get("boundary_coverage", {})),
            ("Negative cases", coverage.get("negative_case_coverage", {})),
        )
    )
    warnings = (
        "".join(
            f"<li>{html.escape(str(item))}</li>" for item in coverage.get("generation_warnings", [])
        )
        or "<li>None</li>"
    )
    body = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Great Generator contract-to-test coverage report</title>
<style>body{{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem;color:#172033}}
table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccd3df;padding:.6rem;text-align:left}}
code{{background:#f2f5f9;padding:.1rem .3rem}}.ok{{color:#137333}}.bad{{color:#b3261e}}</style></head>
<body><h1>Contract-to-Test Coverage Report</h1>
<p>This report contains validation measurements and metadata only. Generated records are not embedded.</p>
<h2>Generation summary</h2><p>Scenarios generated: <strong>{coverage.get('scenarios_generated', 0)}</strong>;
validated: <strong>{coverage.get('scenarios_validated', 0)}</strong>.</p>
<p>Clean baseline validation: <strong class="{'ok' if validation.get('passed') else 'bad'}">
{html.escape(str(bool(validation.get('passed'))))}</strong></p>
<h2>Coverage</h2><table><thead><tr><th>Metric</th><th>Covered</th><th>Total</th><th>Percent</th></tr></thead>
<tbody>{rows}</tbody></table><h2>Warnings and limitations</h2><ul>{warnings}</ul>
<h2>Reproducibility</h2><pre>{html.escape(json.dumps(payload.get('manifest', {}), indent=2, default=str))}</pre>
</body></html>"""
    target.write_text(body, encoding="utf-8")
    return target


def _metric(covered: int, total: int) -> dict[str, Any]:
    return {
        "covered": int(covered),
        "total": int(total),
        "percentage": round((covered / total) * 100.0, 2) if total else None,
    }


def _column(schema: DomainSchema, table_name: str, column_name: str) -> Any:
    return next(
        column for column in schema.tables[table_name].columns if column.name == column_name
    )


def validation_warnings(validation: Mapping[str, Any]) -> list[str]:
    warnings: list[str] = []
    if not validation.get("passed"):
        warnings.append("The clean baseline did not pass all measured validation checks.")
    return warnings
