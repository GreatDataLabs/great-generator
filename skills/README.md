# Great Generator Agent Skills

Reusable workflow instructions, small deterministic helpers and executable examples.
These are optional source-distributed resources, not a second generation engine.
Start with [installation and usage](../docs/AGENT_SKILLS.md).

| Skill | Developer request | Entry point |
|---|---|---|
| Schema test data | "Generate fixtures from this contract" | [schema-test-data](schema-test-data/SKILL.md) |
| Query test data | "Make this SQL test hit its filters and joins" | [query-test-data](query-test-data/SKILL.md) |
| Relational fixtures | "Keep these tables' PK/FKs consistent" | [relational-test-fixtures](relational-test-fixtures/SKILL.md) |
| Pipeline test pack | "Give me happy, boundary, CDC and history cases" | [data-pipeline-test-pack](data-pipeline-test-pack/SKILL.md) |
| Schema regression | "What fixtures change with this schema?" | [schema-change-regression](schema-change-regression/SKILL.md) |
| Databricks test data | "Create Spark fixtures for a disposable Delta target" | [databricks-test-data](databricks-test-data/SKILL.md) |

Copy an entire selected skill directory, including its references/examples/scripts,
into your agent's supported skill location. Sibling skills are optional; routing
never assumes they are installed. The top-level `evaluations` folder is a maintainer
test resource, not a seventh skill. No skills are installed by `pip install` alone.

Run the source-checkout checks:

```bash
python scripts/validate_skills.py
pytest tests/test_agent_skills.py
```

See [evaluations](evaluations/README.md), [audit and MCP mapping](../docs/AGENT_SKILLS_AUDIT.md),
and [Databricks guide](../docs/DATABRICKS_AGENT_SKILL.md). The repository MIT license
applies to these resources. Review helpers before execution; skill discovery does
not authorize writes, database access, uploads or destructive operations.
