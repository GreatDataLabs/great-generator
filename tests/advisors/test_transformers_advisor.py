from __future__ import annotations

import json
import sys
from types import ModuleType

import pandas as pd
import pytest

from great_generator import generate_from_schema
from great_generator.advisors.exceptions import AdvisorResponseError, AdvisorUnavailableError
from great_generator.advisors.registry import get_advisor
from great_generator.advisors.transformers import TransformersAdvisor

_PLAN_JSON = (
    '{"columns":[{"column":"email","dtype":"string","strategy":"semantic.email",'
    '"parameters":{},"rationale":"email field","confidence":0.9,"source":"advisor"}],'
    '"inter_column_rules":[],"notes":null}'
)


def _install_fake_transformers(monkeypatch, responses, calls, *, is_encoder_decoder=True):
    module = ModuleType("transformers")
    encoder_decoder = is_encoder_decoder

    class FakeConfig:
        is_encoder_decoder = encoder_decoder

    class FakeAutoConfig:
        @staticmethod
        def from_pretrained(model_id, **kwargs):
            calls.append(("config", model_id, kwargs))
            return FakeConfig()

    class FakeTokenizer:
        def __call__(self, prompt, **kwargs):
            calls.append(("tokenize", prompt, kwargs))
            return {"input_ids": [[1, 2, 3]]}

        def decode(self, output, skip_special_tokens=True):
            calls.append(("decode", output, {"skip_special_tokens": skip_special_tokens}))
            return responses.pop(0)

    class FakeAutoTokenizer:
        @staticmethod
        def from_pretrained(model_id, **kwargs):
            calls.append(("tokenizer", model_id, kwargs))
            return FakeTokenizer()

    class FakeModel:
        def generate(self, **kwargs):
            calls.append(("generate", kwargs))
            return [[4, 5, 6]]

        def eval(self):
            calls.append(("eval", None, {}))
            return self

    class FakeSeq2Seq:
        @staticmethod
        def from_pretrained(model_id, **kwargs):
            calls.append(("seq2seq", model_id, kwargs))
            return FakeModel()

    class FakeCausal:
        @staticmethod
        def from_pretrained(model_id, **kwargs):
            calls.append(("causal", model_id, kwargs))
            return FakeModel()

    module.AutoConfig = FakeAutoConfig
    module.AutoTokenizer = FakeAutoTokenizer
    module.AutoModelForSeq2SeqLM = FakeSeq2Seq
    module.AutoModelForCausalLM = FakeCausal
    monkeypatch.setitem(sys.modules, "transformers", module)


def test_transformers_not_imported_for_default_advisor(monkeypatch):
    monkeypatch.setitem(sys.modules, "transformers", None)

    advisor = get_advisor(None)

    assert advisor.name == "none"


def test_transformers_missing_dependency_gives_clear_error(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "transformers", None)
    advisor = get_advisor("transformers:google/flan-t5-small", cache_path=tmp_path)

    with pytest.raises(AdvisorUnavailableError, match=r"great-generator\[transformers\]"):
        advisor.propose_plan("email string")


def test_registry_parses_transformers_model_id(tmp_path):
    advisor = get_advisor("transformers:google/flan-t5-small", cache_path=tmp_path)

    assert advisor.name == "transformers:google/flan-t5-small"
    assert advisor.model_id == "google/flan-t5-small"


def test_transformers_advisor_mocked_model_returns_plan(monkeypatch, tmp_path):
    calls = []
    _install_fake_transformers(monkeypatch, [_PLAN_JSON], calls)

    advisor = TransformersAdvisor(model_id="local-test-model", cache_path=tmp_path)
    plan = advisor.propose_plan("email string")

    assert plan.columns[0].strategy == "semantic.email"
    assert advisor.last_cache_hit is False
    assert any(call[0] == "seq2seq" for call in calls)
    assert all(
        call[2].get("local_files_only") is True
        for call in calls
        if call[0] in {"config", "tokenizer", "seq2seq"}
    )


def test_transformers_invalid_json_retries_once(monkeypatch, tmp_path):
    calls = []
    _install_fake_transformers(monkeypatch, ["not json", _PLAN_JSON], calls)

    advisor = TransformersAdvisor(model_id="local-test-model", cache_path=tmp_path)
    plan = advisor.propose_plan("email string")

    assert plan.columns[0].strategy == "semantic.email"
    generate_calls = [call for call in calls if call[0] == "generate"]
    assert len(generate_calls) == 2


def test_transformers_second_invalid_json_raises(monkeypatch, tmp_path):
    calls = []
    _install_fake_transformers(monkeypatch, ["not json", "still not json"], calls)

    advisor = TransformersAdvisor(model_id="local-test-model", cache_path=tmp_path)

    with pytest.raises(AdvisorResponseError):
        advisor.propose_plan("email string")


def test_transformers_cache_entry_includes_model_and_input_hash(monkeypatch, tmp_path):
    calls = []
    schema = "email string"
    _install_fake_transformers(monkeypatch, [_PLAN_JSON], calls)

    advisor = TransformersAdvisor(model_id="local-test-model", cache_path=tmp_path)
    advisor.propose_plan(schema)

    cache_files = list(tmp_path.rglob("*.json"))
    assert len(cache_files) == 1
    payload = json.loads(cache_files[0].read_text(encoding="utf-8"))
    assert payload["advisor"] == "transformers:local-test-model"
    assert payload["model_id"] == "local-test-model"
    assert payload["prompt_version"] == "propose_plan_v1"
    assert len(payload["input_hash"]) == 64


def test_generation_with_transformers_saved_plan_remains_deterministic(monkeypatch, tmp_path):
    calls = []
    _install_fake_transformers(monkeypatch, [_PLAN_JSON], calls)
    advisor = TransformersAdvisor(model_id="local-test-model", cache_path=tmp_path)
    plan = advisor.propose_plan("email string")

    left = generate_from_schema("email string", rows=10, plan=plan, seed=42)
    right = generate_from_schema("email string", rows=10, plan=plan, seed=42)

    pd.testing.assert_frame_equal(left, right)
