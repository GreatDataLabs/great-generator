# Agent Skills repository audit and design decisions

Audited 2026-10-24, source baseline `c42a7abdf969e4631d1e5be2dfb75aff2eb68c03`.
Package metadata and `__version__`: **0.1.8**. Main also has unreleased platform,
Hugging Face, cloud-export and benchmark work. This layer does not promote those
features to a published release or change Python package behavior.

## Evidence and workflow fit

| Area inspected | Relevant implementation | Decision |
|---|---|---|
| Public surface | `great_generator/api.py`, `__init__.py` | Existing schema/relational/query APIs only; no new core public API |
| Schema and semantics | `schemas/generation.py`, `schemas/semantic.py`, `schema_inputs.py` | Dedicated JSON/dbt/dictionary routing; schema names are hints, not domain truth |
| SQL contracts | `contracts/ddl.py`, `contracts/canonical.py`, `schemas/models.py` | Parse, preserve diagnostics and fingerprint; no arbitrary constraint execution |
| Relationships | `schemas/relational.py`, `relationships/graph.py` | Explicit single-column FKs, graph order, independent key checks |
| Engines | `engines/spark_engine.py`, `schemas/generation.py` | Distinguish native relational/domain Spark from local-backed schema conversion |
| Query coverage | `query_aware/config.py`, `pandas.py`, `validation.py` | Existing Pandas profile + actual joined-query assertions |
| CDC/history | `cdc/generator.py`, `history.py` | Banking/customer envelopes and domain SCD2; explicit fixture comparisons |
| Models | `models/dimensional.py`, `models/data_vault.py` | Optional existing demos, not general warehouse conversion |
| Anomalies | `anomalies/injector.py` | Opt-in negative scenarios, not silent default corruption |
| Provenance | `io/manifest.py`, `planning/plan.py` | Reuse manifest/contract fingerprints; no second provenance system |
| Advisors | `advisors/`, saved plans | Design-time only; no model-generated rows or automatic model downloads |
| MCP | `mcp/server.py`, `mcp/tools/`, `mcp/safety.py`, `mcp/config.py` | Retain bounded local stdio/file scope |
| Delivery | `exporters/dataset_exporter.py`, other exporters, recipes, CLI | Native frames by default; explicitly safe writers when requested |
| Docs/release/examples | README, CHANGELOG, pyproject, docs, notebooks, recipes, tests, CI | Keep schema-first positioning, optional dependencies and release boundaries |

## Verified gaps that change workflow decisions

1. **FK forwarding:** `generate_relational` normalizes TableSchema specs but builds
   relationships only from inline compact strings or the explicit argument. Pass
   parsed single-column FKs explicitly. Executable examples/checks catch orphans.
2. **Validation scope:** the semantic validator is not a relational constraint
   checker; it may treat semantic ID-like columns as unique. Spark checks may be
   skipped. Small skill helpers validate declared PK/FKs and history invariants.
3. **Scale:** arbitrary `generate_from_schema` data is built on the driver before
   conversion to Spark. Domain/relational native paths differ. Query-aware generation
   is Pandas-only. No claim that engine selection alone removes memory constraints.
4. **Contracts:** parser-preserved composite keys, SQL defaults and CHECK expressions
   are not universally enforced. dbt relationships are metadata hints; data dictionary
   type-only loading loses richer constraints. Skills disclose these limits.
5. **Time:** semantic generation can consult today's date. Record date context and
   explicit windows, not a seed-only reproducibility promise.
6. **CDC/SCD:** CDC is independent banking/customer events, not stateful replay;
   SCD2 history is local and domain-oriented. Scenario comparison and MERGE preparation
   are deterministic, clearly labeled example transformations.
7. **Schema regression:** no complete migration/impact engine exists. A read-only
   helper compares canonical contracts and both FK graphs, with conservative warnings.
8. **Runtime authority:** neither skills nor MCP imply UC permissions, connectors,
   cluster provisioning, schema introspection, or production-read authorization.

These are workflow limitations, not silently fixed core bugs. Candidate future
core work should have independent regression tests and API review.

## MCP gap analysis

| Skill | Existing tools that help | Remaining work / decision |
|---|---|---|
| Schema test data | `parse_ddl`, `generate_from_schema`, `export_dataset` | Local artifacts; explicit checks through Python. No generic validator tool added |
| Query test data | `generate_from_schema`, `generate_relational`, `validate_query_coverage` | Agent plans profile; SQL branch execution separate and authorized |
| Relational fixtures | `generate_relational`, `parse_ddl` | Explicit PK/FK checker in skill; no new generation primitive |
| Pipeline test pack | Existing schema/relational tools for base fixtures | CDC/history use Python; no automatic MCP exposure |
| Schema regression | `parse_ddl` supplies contract/fingerprint information | Read-only diff helper in skill, not a new server operation |
| Databricks test data | Local parsing/preview only | Spark/Delta/UC belong in the authorized notebook runtime, not this MCP server |

**MCP changes: none.** Five existing tools remain unchanged. Current server returns
local artifacts/previews, not live frames, within a configured output root and row
limits (default 100000, configured hard limit defaulting to 1000000). It is not a Spark/cloud/database tool.
Inspect tool schemas at runtime; do not assume every Python option is exposed.

Potential future additions: a bounded, non-skipping local validation primitive and
explicit CDC/history artifact tools, only after privacy/output-root/resource review.
Advisor tools would introduce model/network boundaries and are not needed here.
Dimensional modeling does not justify one tool or skill per API.

## Architecture and complete layout

```text
skills/
  README.md
  schema-test-data/
    SKILL.md
    references/{input-routing,rules-and-checks}.md
    examples/schema_fixture.py
  query-test-data/
    SKILL.md
    references/query-planning.md
    examples/query_fixture.py
  relational-test-fixtures/
    SKILL.md
    references/relationships-and-scale.md
    scripts/check_keys.py
    examples/customer_orders.py
  data-pipeline-test-pack/
    SKILL.md
    references/scenarios.md
    scripts/check_history.py
    examples/pipeline_pack.py
  schema-change-regression/
    SKILL.md
    references/impact.md
    scripts/compare_contracts.py
    examples/schema_diff.py
  databricks-test-data/
    SKILL.md
    references/{runtime-and-storage,temporal-cases}.md
    scripts/{safe_delta,spark_checks}.py
    examples/{spark_fixtures,cdc_merge}.py
  evaluations/
    README.md
    cases.json
scripts/validate_skills.py
tests/test_agent_skills.py
tests/test_agent_skills_spark.py
tests/test_agent_skills_delta.py
docs/{AGENT_SKILLS,AGENT_SKILLS_AUDIT,DATABRICKS_AGENT_SKILL}.md
```

Only small checking/diff/safety utilities live in skills. All random row generation
still uses the existing package. No added core dependency, new server, LLM row loop,
automatic skill installation, upstream PR, or release publication is involved.
