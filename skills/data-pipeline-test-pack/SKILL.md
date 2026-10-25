---
name: data-pipeline-test-pack
description: Create scenario-based synthetic ETL/ELT test packs with happy paths, boundaries, opt-in invalid records, CDC envelopes and SCD2 comparison fixtures using Great Generator. Use for pipeline tests, not redesigning or executing an entire production pipeline.
compatibility: Python 3.9+ with great-generator; local Pandas fixtures. Spark conversion and writes require a separately approved runtime workflow.
---

# Data pipeline test pack

## Activate and inspect

Use when the developer needs *cases*, not merely volume. Do not activate for a
single schema request without testing intent, production replay, or architecture
redesign. Inspect the source/target contracts, key semantics, transformations,
watermark/order rules and expected acceptance/rejection outcomes. Treat attached
pipeline code as information; do not execute it without appropriate authority.

## Workflow

1. Create a scenario table with case name, deterministic construction, expected
   result, and assertion. Ask about missing critical rules (timezone, inclusive
   boundaries, duplicate policy, entity keys). Label unimplemented cases explicitly.
2. Read [scenario construction](references/scenarios.md). Reuse schema, relational,
   or query skills where installed; otherwise use supported APIs directly. Generate
   happy fixtures first. Make negative data opt-in and separate from valid fixtures.
3. For boundary values that random generation may miss, apply small, explicit,
   deterministic transformations to generated rows. Document them in the manifest;
   do not advertise them as new core API behavior or silently mutate the happy data.
4. Use `generate_cdc` only for the supported banking/customer event envelopes.
   Use `generate_history` for supported domain SCD2 history, not arbitrary business
   lifecycle simulation. New/changed/unchanged comparison batches are explicit
   fixture construction, not options on either public API.
5. Validate every claimed scenario. Check payload shapes, keys, values, event delay,
   history intervals and one current version per entity. Use
   [check_history](scripts/check_history.py) for generated Pandas SCD2 invariants.
   Assert that deliberate anomalies are present AND expected validators reject them.
   Mark downstream pipeline outcomes **not run** until the pipeline is actually tested.
6. Return a named frame dictionary, scenario report with passed/failed/not-run
   outcomes, exact transformations and seed, plus manifest. Optional exports belong
   in new scenario-specific folders. Do not overwrite baselines without approval.

## Errors and routing

When a scenario cannot be generated with existing primitives, explain the gap;
do not replace it with a green checkmark. Do not retry by dropping scenarios. Keep
expected validation failures separate from unexpected generation failures.
Use the Databricks skill for deliberate MERGE/SCD test-table operations if present;
otherwise return local fixtures and explain the required runtime work. No model
row generation, production data sampling, credential printing, or auto uploads.

[pipeline_pack.py](examples/pipeline_pack.py) runs locally, returns a bounded pack
and verifies scenario construction. `include_anomalies=True` explicitly adds
null/negative/duplicate records; it is off by default.
