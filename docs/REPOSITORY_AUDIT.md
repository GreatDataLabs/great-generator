# Repository Audit

This audit captures the public surface and launch-readiness state reviewed before the repository-hardening changes in this phase.

## Scope reviewed

- `README.md`
- `pyproject.toml`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- public package imports in `great_generator/__init__.py`
- compatibility imports in `enterprise_synth/__init__.py`
- command-line entry point in `great_generator/cli.py`
- tests under `tests/`, including advisor, planning, schema, relational, domain, export, and Spark suites
- documentation under `docs/`
- examples under `examples/`
- GitHub Actions workflows under `.github/workflows/`
- benchmark harness under `benchmarks/`

## Public API observed

The top-level package exports the primary generation, export, validation, planning, and metadata functions documented in the README: `generate_from_schema`, `generate_relational`, `parse_ddl`, `generate_domain`, `generate_cdc`, `generate_history`, `generate_dimensional_model`, `generate_data_vault_model`, `generate_from_recipe`, `export_data`, `validate_generated_data`, `explain_generation_plan`, `infer_generation_plan`, `tag_schema`, `review_realism`, `list_domains`, and `get_domain_schema`.

The console script is:

```bash
great-generator
```

The backward-compatible import namespace remains:

```python
import enterprise_synth
```

## Packaging state

- Package name: `great-generator`
- Import name: `great_generator`
- Current package version in `pyproject.toml`: `0.1.8`
- Python support: `>=3.9`
- Required runtime dependencies: Pandas, NumPy, PyArrow, Faker, and SQLGlot.
- Spark, Delta, advisor, dbt/schema-ingestion, MCP, and development dependencies are optional extras.
- `great_generator` and `enterprise_synth` are both included in the built wheel.

## Baseline validation results

Validation was run before implementing this phase.

| Check | Result | Notes |
|---|---:|---|
| Advisor and planning tests | Passed | 24 tests |
| Contract DDL tests | Passed | 22 tests |
| Core non-Spark tests | Passed | 131 tests run file-by-file because the complete suite exceeds short local command timeouts |
| Spark tests | Passed | 21 tests; local Windows Spark startup is slow but successful |
| Ruff | Passed | `ruff check .` |
| Black | Passed | `black --check .` |
| Build and Twine check | Passed | sdist and wheel built; `twine check dist/*` passed |
| Mypy | Baseline issues | Optional advisor extras report missing optional stubs/imports and two protocol return mismatches |

## Launch-readiness observations

Strengths:

- The schema-first positioning is clear and differentiated from single-value fake data generation.
- `generate_from_schema` already supports mappings, DataFrames, DDL strings, Spark schemas, and parsed DDL contracts.
- `generate_relational` supports user-defined related tables and returns DataFrames instead of forcing export.
- Domain packs, CDC, anomalies, dimensional models, Data Vault models, and Spark/Delta exports are documented as secondary/advanced APIs.
- PyPI metadata, project links, documentation site, tests, and release workflows exist.

Gaps addressed in this phase:

- A flagship, runnable star-schema example was missing.
- Determinism needed a dedicated user-facing contract.
- General generation manifests needed a documented shape that does not conflict with existing advisor metadata.
- Benchmark methodology needed clearer environment-dependent language and reproducible JSON output.
- Contributor guidance needed clearer contribution tracks.
- Citation metadata was missing.

Deferred gaps:

- Mypy cleanup for optional advisor extras should be handled as a focused typing pass.
- Full composite-key relational generation remains a larger relational-modeling milestone.
- Great Expectations and Pandera integrations should start as examples/design docs before adding optional runtime dependencies.
