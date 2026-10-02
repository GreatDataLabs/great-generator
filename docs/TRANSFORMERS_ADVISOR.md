# Transformers Advisor

`TransformersAdvisor` is an optional design-time advisor backed by local Hugging Face Transformers models.

It can help propose generation plans, tag columns, or review generated samples. It does **not** generate row data.

Generation remains deterministic from:

- schema
- saved generation plan
- generation arguments
- seed

## What it does

- Loads a local or cached Transformers model.
- Sends schema metadata, hints, or sample summaries to the model.
- Requests strict JSON output.
- Validates the JSON response.
- Converts valid responses into Great Generator planning artifacts.
- Uses the existing advisor cache.

## What it does not do

- It does not generate rows.
- It does not call hosted inference APIs.
- It does not upload data.
- It does not guarantee model quality.
- It does not replace human review for important datasets.

## Installation

```bash
pip install "great-generator[transformers]"
```

For dataset conversion and card helpers as well:

```bash
pip install "great-generator[hf-full]"
```

## Local model usage

```python
from great_generator import generate_from_schema, infer_generation_plan

schema = """
customer_id int,
customer_name string,
email string,
signup_date date,
account_status string
"""

plan = infer_generation_plan(
    schema,
    advisor="transformers:google/flan-t5-small",
)

df = generate_from_schema(schema, rows=1000, plan=plan, seed=42)
```

By default, `TransformersAdvisor` uses `local_files_only=True`. This prevents implicit network downloads. Use a local model path or pre-populate the Hugging Face cache before running the advisor.

Advanced users who explicitly allow downloads in their environment can instantiate the advisor directly:

```python
from great_generator.advisors.transformers import TransformersAdvisor

advisor = TransformersAdvisor(
    model_id="google/flan-t5-small",
    local_files_only=False,
)
plan = advisor.propose_plan("customer_id int, email string")
```

## Determinism boundary

The model may be used to create a plan at design time. Once a plan is saved, deterministic generation consumes the plan and seed. The model is not involved in row generation.

```python
plan.to_json("plan.json")

# Later, use the reviewed plan deterministically.
df = generate_from_schema(schema, rows=1000, plan=plan, seed=42)
```

## Caching

Advisor responses use the existing advisor cache. Cache keys include:

- advisor name
- model id
- prompt version
- input hash

Use `refresh_cache=True` when calling public advisor APIs if you intentionally want a fresh response.

## JSON validation

The advisor prompts request strict JSON. If a model returns invalid JSON, Great Generator retries once with a stricter instruction. If the response is still invalid, an `AdvisorResponseError` is raised.

Great Generator never executes model output as code.

## Model quality limitations

Small local models are convenient but may produce weak plans. Larger local models may produce better plans but require more memory and setup. Always inspect generated plans before using them for important datasets.

## Troubleshooting

### Missing optional dependency

Install the optional extra:

```bash
pip install "great-generator[transformers]"
```

### Model cannot be loaded locally

By default, Great Generator asks Transformers to load local files only. Use a local model path, pre-download/cache the model, or explicitly set `local_files_only=False` if downloads are acceptable in your environment.

### Invalid JSON response

Try a stronger instruction in `hints`, a different model, or manually edit the generated plan.

## Upstream listing note

After a working TransformersAdvisor and examples are available, a small PR proposing Great Generator for the Transformers project list may be considered. Any upstream PR should follow the current Transformers contribution guide, avoid pure agent-generated submissions, include tests or evidence, and clearly explain the integration.
