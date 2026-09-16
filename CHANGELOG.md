# Changelog

All notable changes to this project will be documented here.

This project follows semantic versioning once public releases begin.

## Release summary

| Version | Date | Release focus | Main changes |
|---|---:|---|---|
| Unreleased | TBD | Next improvements | No unreleased changes yet |
| 0.1.8 | 2026-09-16 | Schema ingestion, optional MCP server, org documentation, and architecture | JSON Schema ingestion, dbt metadata ingestion, CSV/YAML/JSON data dictionary ingestion, query-aware examples, optional `great-generator[mcp]` extra, local-file MCP tools, safety controls, tests, sitemap, robots.txt, SEO metadata, GreatDataLabs documentation links, and architecture diagram |
| 0.1.7 | 2026-08-15 | SQL DDL contracts and query-aware generation | Canonical contracts, `parse_ddl(...)`, stable contract hashing, structured parser diagnostics, documented ANSI/Spark/Databricks `CREATE TABLE` subset, optional query-aware generation, a runnable retail star-schema example, generation manifests, determinism docs, benchmark methodology, and citation metadata |
| 0.1.6 | 2026-07-11 | AI advisor planning layer | Optional design-time advisors, editable plans and tags, advisor cache, manifest metadata, and deterministic `plan=` support for schema generation |
| 0.1.5 | 2026-06-28 | Schema-first docs and Spark database writes | Schema-first README, support matrix, Databricks and PySpark examples for Snowflake and Azure SQL, and documentation site updates |
| 0.1.4 | 2026-06-21 | PyPI author presentation | Author section and project links for PyPI |
| 0.1.3 | 2026-06-21 | PyPI metadata visibility | Package metadata updates for author and maintainer visibility |
| 0.1.2 | 2026-06-21 | Schema realism quality | Semantic-field generation, custom rules, validation reports, and realistic schema defaults |
| 0.1.1 | 2026-06-20 | Advanced generation APIs | Anomaly labels, SCD2 history, recipes, CLI, dimensional models, and Data Vault models |
| 0.1.0 | 2026-06-19 | Initial public release | Package identity, domain packs, Pandas and Spark engines, exports, CDC, anomalies, schema generation, and relational generation |

## Unreleased

No unreleased changes yet.

## 0.1.8 - 2026-09-16

Schema-source ingestion, optional MCP tooling, website search discovery, organization-link migration, and architecture documentation release.

### Added

- Added JSON Schema ingestion for schema-first synthetic data generation.
- Added dbt `schema.yml` and `manifest.json` ingestion for analytics engineering workflows.
- Added data dictionary ingestion from CSV, YAML, and JSON schema documentation.
- Added documentation for schema input options and query-aware generation examples.
- Added release consistency tests for package version and changelog coverage.
- Added an optional MCP server under the existing `great-generator[mcp]` extra.
- Added CLI entry point: `great-generator-mcp`.
- Added MCP tools for `generate_from_schema`, `parse_ddl`, `generate_relational`, `validate_query_coverage`, and `export_dataset`.
- Added path safety, row limits, overwrite protection, local output manifests, JSON-safe responses, and preview-only dataset responses for MCP tools.
- Added MCP documentation, README updates, wiki update copy, architecture diagrams, ecosystem diagrams, example client configurations, and tests.
- Added search discovery files for the GitHub Pages site, including `sitemap.xml` and `robots.txt`.
- Added SEO metadata, canonical URLs, Open Graph metadata, Twitter/X card metadata, and structured data for the project website.
- Added SEO maintenance documentation and a sitemap regeneration script.
- Added the enterprise platform architecture diagram to the README and GitHub Pages documentation site.

### Changed

- Aligned README, package version, changelog, citation metadata, and PyPI release documentation around the `0.1.8` package version.
- Updated repository, documentation, sitemap, robots, canonical, Open Graph, and project metadata links to the GreatDataLabs GitHub organization and GitHub Pages site.

## 0.1.7 - 2026-08-15

SQL DDL contracts and query-aware generation release.

### Added

- Added `ContractSchema` as a canonical contract container for schema-qualified multi-table metadata.
- Added stable canonical contract serialization and SHA-256 contract fingerprints.
- Added `parse_ddl(...)` for SQL `CREATE TABLE` ingestion using SQLGlot.
- Added structured DDL parser diagnostics with strict and permissive parsing modes.
- Added support for the documented ANSI, Spark, and Databricks scalar DDL subset, including primary keys, composite keys, foreign keys, composite foreign keys, unique constraints, check constraints, defaults, comments, and selected Databricks/Spark metadata.
- Added generation integration so one-table parsed DDL contracts can generate DataFrames through `generate_from_schema(...)`.
- Added contract and DDL documentation, ADRs, an example, and parser tests.
- Added a runnable retail star-schema example with DDL, deterministic business rules, relationship validation, Spark/Databricks usage notes, and manifest output.
- Added a general `build_generation_manifest(...)` helper for lightweight provenance metadata.
- Added determinism, provenance, benchmark methodology, recipe-authoring, and data-quality integration design documentation.
- Added `CITATION.cff` for research, teaching, and demo citation workflows.
- Added optional query-aware generation for schema and relational data.
- Added `required_values` support to ensure expected query filter values appear in generated data.
- Added query-aware `partition_by` support for balanced and custom partition-date generation.
- Added optional `target_selectivity` support for approximate filter-value ratios.
- Added optional relational join coverage for fact and dimension query testing.
- Added `validate_query_coverage(...)` for required-value, partition, selectivity, and join coverage reports.

### Changed

- Extended existing `ColumnSpec`, `TableSchema`, `DomainSchema`, and `ForeignKey` models without removing their existing public constructors.
- Updated planning and no-op advisor paths to understand `ContractSchema`.
- Improved the local Pandas benchmark runner with selected cases, repeat runs, environment metadata, and optional JSON output.

### Deferred

- Full composite-key and cyclic relational generation is deferred to a later relational milestone. M1A parses that metadata but does not claim complete generation strategy support for those advanced cases.

## 0.1.6 - 2026-07-11

AI advisor planning release.

### Added

- AI advisor layer for design-time schema understanding, column tagging, and realism review. Opt-in. Deterministic path unchanged.
- Advisors: NoOp default, Anthropic, Ollama. OpenAI and llama.cpp stubs.
- `GenerationPlan` and `ColumnTags` as inspectable, editable JSON artifacts.
- Manifest enrichment recording advisor contribution.
- New extras: `[ai]`, `[anthropic]`, `[openai]`, `[ollama]`, `[llamacpp]`.

### Changed

- `generate_from_schema(...)` now accepts an optional `plan=` argument. Existing behavior is unchanged when `plan=None`.
- README and API docs now describe the advisor layer, offline Ollama usage, caching, prompt safety, and plan review.

### Fixed

- Added a prompt package marker so advisor prompt files load correctly on Python 3.9.

## 0.1.5 - 2026-06-28

Schema-first documentation and Spark database integration release.

### Added

- Added a GitHub Pages documentation landing site under `docs/index.html` with install, examples, platform guidance, feature coverage, and project links.
- Added `docs/GITHUB_PAGES.md` with setup instructions for publishing the site with GitHub Actions or from the `main` branch and `/docs` folder.
- Added `.github/workflows/pages.yml` to enable and publish the static documentation site through GitHub Pages.
- Added a complete schema input support matrix with supported, partial, and planned input types.
- Added schema-first examples for mappings, compact DDL, Pandas dtypes and DataFrames, PySpark StructType and DataFrames, and TableSchema.
- Added Spark and Databricks write examples for Snowflake through the Snowflake Spark Connector.
- Added Spark JDBC write examples for Azure SQL using the Microsoft SQL Server JDBC driver.
- Added focused Spark database-write documentation covering connectors, secrets, authentication, and operational guidance.

### Changed

- Updated README and package project links to point documentation users to the public documentation site while keeping the GitHub Wiki linked for deeper guides.
- Repositioned `generate_from_schema(...)` as the primary workflow for lower-environment data generation, testing, QA, and data engineering.
- Positioned `generate_relational(...)` immediately after schema generation as the primary path for user-defined connected tables.
- Moved `generate_domain(...)` into its secondary role for ready-made demonstrations, tutorials, and learning datasets.
- Updated the README, documentation site, package metadata, examples, and Wiki with accurate schema support and DataFrame write patterns.

## 0.1.4 - 2026-06-21

PyPI author presentation release.

### Changed

- Added a PyPI-friendly Author section with project links in the README.
- Updated the package documentation project link to the GitHub Wiki.

## 0.1.3 - 2026-06-21

PyPI metadata visibility release.

### Changed

- Updated package metadata so PyPI displays the author and maintainer name directly, with contact details available through project links and README.

## 0.1.2 - 2026-06-21

Schema realism quality release.

### Added

- Semantic-field based schema generation for `generate_from_schema(...)`, including abbreviation-aware column inference, realistic schema values, domain presets, custom rules, cross-field consistency, mapping schemas, and `validate_generated_data(...)`.
- Clean realistic schema data-quality rules for ages, dates, lifecycle ordering, ID safety, status-aware nulls, amount formulas, validation summaries, and semantic coverage reports.
- `explain_generation_plan(...)` for inspecting semantic inference before generating rows.
- Optional `validate=True` and `return_report=True` support for `generate_from_schema(...)`.

### Changed

- `generate_from_schema(...)` now defaults to realistic schema values. Use `realistic=False` or `realism="placeholder"` for the older placeholder-style output.
- `realism` now supports friendly aliases: `basic` and `simple` map to placeholder mode, `clean` maps to realistic mode, and the common typo `realsitic` maps to `realistic` with a warning.

## 0.1.1 - 2026-06-20

Advanced generation release.

### Added

- Labeled anomaly ground truth with `_anomaly_labels` for pandas anomaly injection.
- SCD2 history generation through `generate_domain(..., history="scd2")` and `generate_history(...)`.
- Command line interface through `great-generator`.
- Dataset recipes through `generate_from_recipe(...)` and `great-generator run`, supporting JSON, TOML, and simple YAML recipes.
- Dimensional model generation through `generate_dimensional_model(...)`, including domain-aware facts and dimensions for ecommerce and banking.
- Data Vault model generation through `generate_data_vault_model(...)`, including hubs, links, satellites, hash keys, load dates, and record sources.
- Advanced capabilities documentation and RFCs for planned optional extras such as ingestion, streaming, quality integrations, vectors, LLM document generation, fit-from-sample, differential privacy, ML training data, and provenance research.

### Changed

- README and API reference now document the advanced generation APIs.
- Optional-extra namespace now reserves `ingest`, `streaming`, `quality`, `vectors`, `llm`, `fit`, `dp`, and `all`.

## 0.1.0 - 2026-06-19

Initial public PyPI release.

### Added

- Great Generator package identity: publish as `great-generator` and import as `great_generator`.
- Backward-compatible `enterprise_synth` import alias for pre-release users of the earlier repo name.
- Faker-backed realistic value generation for pandas outputs.
- Spark-native deterministic realistic value generation for Spark outputs.
- `realism` mode for domain, relational, and schema generation APIs.
- Realistic customer, patient, resident, user, merchant, product, provider, organization, company, phone, email, address, city, state, and postal-code fields where applicable.
- Curated domain reference values for banking, ecommerce, healthcare, insurance, telecom, manufacturing, logistics, energy, hospitality, SaaS, public sector, media, and automotive-style data.
- Ecommerce domain pack with customers, products, orders, order items, payments, shipments, and returns.
- Banking domain pack with customers, accounts, transactions, cards, merchants, fraud events, and CDC-style customer changes.
- Healthcare domain pack with patients, providers, facilities, encounters, claims, prescriptions, and lab results.
- Telecom domain pack with customers, plans, devices, subscriptions, usage events, invoices, and support tickets.
- Logistics domain pack with shippers, warehouses, carriers, products, shipments, shipment events, and inventory movements.
- SaaS domain pack with organizations, users, plans, subscriptions, features, usage events, invoices, and support tickets.
- Insurance domain pack with customers, agents, policies, claims, premium payments, risk assessments, and reinsurance contracts.
- Automotive domain pack with customers, dealers, vehicles, sales, service appointments, warranty claims, and telematics events.
- Energy domain pack with customers, sites, meters, rate plans, usage readings, outages, and bills.
- Manufacturing domain pack with suppliers, plants, products, work orders, production runs, quality inspections, and inventory movements.
- Media domain pack with users, content titles, subscriptions, viewing events, ad campaigns, ad impressions, and game sessions.
- Public sector domain pack with residents, agencies, programs, applications, cases, payments, and service requests.
- Hospitality domain pack with customers, properties, rooms, reservations, stays, payments, and reviews.
- Shared industry-domain generator for compact domain packs with valid relationships and domain-looking values.
- Schema-driven Spark fallback for newer domain packs, preserving primary-key and foreign-key consistency.
- Deterministic generation with seeds.
- Pandas generation engine.
- Optional Spark generation engine.
- CSV, JSON, Parquet, and Delta export helpers.
- Cloud-friendly Spark path handling for local paths, DBFS, S3, ADLS, and GCS-style URIs.
- Spark export controls for writer options, partitioning, repartitioning, and coalescing.
- CDC generation for banking customer changes.
- Opt-in anomaly injection for nulls, duplicates, orphan keys, late records, out-of-order records, outliers, negative amounts, invalid statuses, and skew.
- Schema-first generation from compact schema strings, pandas DataFrames, PySpark StructTypes, and PySpark DataFrames.
- Custom relational schema generation with user-provided tables, row counts, primary keys, foreign keys, pandas/Spark output, and optional exports.
- Realistic-value examples, documentation pages, a GitHub Wiki, and a lightweight pandas benchmark script.
- Tests for realistic value quality, placeholder compatibility, seed reproducibility, and relationship safety.
- Tests for domain generation, relationship integrity, exports, CDC, anomalies, seed reproducibility, schema generation, and optional Spark behavior.

### Notes

- Spark and Delta dependencies are optional extras.
- JSON-native nested payload generation is planned for a future release.
