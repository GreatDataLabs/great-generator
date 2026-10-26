"""Contract-driven, coverage-aware synthetic data testing APIs."""

from great_generator.testing.compiler import ContractTestResult, compile_test_dataset
from great_generator.testing.constraint_planner import UnsatisfiableScenarioError
from great_generator.testing.query_contract import (
    CoverageScenario,
    QueryContract,
    QueryDiagnostic,
    WorkloadContract,
)
from great_generator.testing.workload_parser import parse_sql_workload

__all__ = [
    "ContractTestResult",
    "CoverageScenario",
    "QueryContract",
    "QueryDiagnostic",
    "UnsatisfiableScenarioError",
    "WorkloadContract",
    "compile_test_dataset",
    "parse_sql_workload",
]
