# Advisor layer

The advisor layer helps at design time. It can infer a generation plan, tag schema columns, and review a generated sample. It does not generate row data.

The default advisor is `advisor="none"`. In that mode Great Generator makes no model calls, reads no API keys, and sends nothing over the network.

## What advisors do

Advisors can produce:

- `GenerationPlan`, an editable JSON plan for how columns should be generated
- `ColumnTags`, editable JSON tags for PII class, business semantic, and suggested masking
- `RealismReport`, a design-time review of a generated sample against a plan

Advisors do not:

- create per-row values
- repair generation errors
- infer relationships between tables
- accept natural language as a schema entry point
- run generated code

## Determinism guarantee

Generation is deterministic. Advisors run before generation and produce artifacts. Generation consumes those artifacts.

```text
schema -> advisor -> plan -> generation -> data
```

Given the same schema, plan, seed, and generation arguments, output should be the same. If you edit a plan, save it as JSON and treat it as part of your test fixture.

## Choosing an advisor

| Advisor spec | Status | Network | Requirements | Use when |
|---|---|---:|---|---|
| `none` | Default | No | Base package | You want no model calls and dtype-based defaults |
| `anthropic:claude-sonnet-4-6` | Supported | Yes | `great-generator[anthropic]`, `ANTHROPIC_API_KEY` | You want an online model to suggest plans and tags |
| `ollama:llama3.1:8b` | Supported | Local only | Ollama running on the machine | You want offline or private local review |
| `transformers:google/flan-t5-small` | Supported | No by default | `great-generator[transformers]`, local or cached model files | You want a local Hugging Face Transformers model for design-time planning |
| `openai:gpt-4o-mini` | Stub | Not used | Not implemented in v1 | Planned path |
| `llamacpp:/path/to/model.gguf` | Stub | Not used | Not implemented in v1 | Planned path |

## Transformers usage

Install the optional extra:

```bash
pip install "great-generator[transformers]"
```

Use a local or cached model:

```python
from great_generator import infer_generation_plan

plan = infer_generation_plan(
    "customer_id int, email string",
    advisor="transformers:google/flan-t5-small",
)
```

The Transformers advisor runs at design time only. It produces plans, tags, or reports. It does not generate row data. By default, it loads local files only so it does not implicitly download models. See [Transformers Advisor](TRANSFORMERS_ADVISOR.md).

## Offline usage with Ollama

Install Ollama, start the local service, and pull a model:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
ollama pull llama3.1:8b
```

On macOS or Windows, install Ollama from [ollama.com/download](https://ollama.com/download), then run:

```bash
ollama pull llama3.1:8b
```

Use the local advisor:

```python
from great_generator import infer_generation_plan

plan = infer_generation_plan(
    "customer_id int, customer_name string, email string",
    advisor="ollama:llama3.1:8b",
)
```

By default the Ollama advisor calls `http://localhost:11434`. Set `OLLAMA_HOST` if your local server uses a different address.

## Anthropic usage

Install the extra and set an API key:

```bash
pip install "great-generator[anthropic]"
export ANTHROPIC_API_KEY="..."
```

Then call:

```python
from great_generator import infer_generation_plan

plan = infer_generation_plan(
    "customer_id int, customer_name string, email string",
    advisor="anthropic:claude-sonnet-4-6",
)
```

## Caching

Advisor calls are cached under `.gg_cache/` by default.

Each cache entry is keyed by:

```text
advisor_name + model_id + prompt_version + canonical_input_json
```

The cache layout is:

```text
.gg_cache/
  anthropic/
    ab/
      abc123...json
  ollama/
    cd/
      cde456...json
```

Each entry stores:

- cache key
- advisor
- model id
- prompt version
- input hash
- response
- created timestamp

Use `refresh_cache=True` to bypass the cache for one call:

```python
plan = infer_generation_plan(
    schema,
    advisor="ollama:llama3.1:8b",
    refresh_cache=True,
)
```

You can also delete `.gg_cache/` manually.

## Editing plans by hand

Plans are JSON. You can save, inspect, edit, and commit them.

```python
from great_generator import infer_generation_plan

plan = infer_generation_plan("customer_id int, customer_name string")
plan.to_json("plans/customer_plan.json")
```

Example snippet:

```json
{
  "human_reviewed": false,
  "columns": [
    {
      "column": "customer_name",
      "dtype": "string",
      "strategy": "semantic.full_name",
      "parameters": {},
      "rationale": "Name-like field.",
      "confidence": 0.92,
      "source": "advisor"
    }
  ]
}
```

Programmatic edits mark the plan as reviewed:

```python
reviewed = plan.with_edit(
    "customer_name",
    strategy="semantic.full_name",
    confidence=1.0,
    rationale="Reviewed by data team.",
)
```

`with_edit(...)` returns a new plan, sets the edited column `source` to `user_edit`, and sets `human_reviewed=True`.

## Manifest enrichment

When a plan is used, a manifest can include advisor metadata:

```json
{
  "advisor": {
    "name": "anthropic:claude-sonnet-4-6",
    "model_id": "claude-sonnet-4-6",
    "plan_version": "1.0",
    "plan_fingerprint": "sha256:...",
    "called_at": ["schema_understanding", "column_tagging"],
    "cache_hit": true,
    "columns_tagged": 23,
    "human_reviewed": false
  }
}
```

This is additive metadata. Existing manifest fields are not renamed or removed.

## Prompt safety

Any schema text, column description, hint, or sample value sent to an advisor is treated as untrusted input. Prompt files place user-supplied content inside a `<user_input>...</user_input>` block. Advisor output is parsed as JSON and never executed as code. The library does not use `eval`, shell interpolation, or dynamic imports based on advisor output.
