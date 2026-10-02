"""Transformers-backed design-time advisor.

The advisor is intentionally conservative: local Transformers models may propose
plans, tags, or reports, but they never generate row data. Deterministic row
generation still happens through Great Generator from a saved plan and seed.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from great_generator.advisors import cache
from great_generator.advisors._json_utils import parse_json_object
from great_generator.advisors._prompting import SYSTEM_PROMPT, render_prompt
from great_generator.advisors._validation import (
    plan_from_advisor_payload,
    report_from_advisor_payload,
    tags_from_advisor_payload,
)
from great_generator.advisors.exceptions import AdvisorResponseError, AdvisorUnavailableError
from great_generator.planning import GenerationPlan, canonical_schema
from great_generator.planning.plan import canonical_json

DEFAULT_TRANSFORMERS_MODEL = "google/flan-t5-small"
OPTIONAL_DEPENDENCY_MESSAGE = 'Transformers advisor support is optional. Install with: pip install "great-generator[transformers]"'


class TransformersAdvisor:
    """Advisor backed by local Hugging Face Transformers models.

    By default, ``local_files_only`` is true so using this advisor does not make
    network calls implicitly. Use a local model path or pre-populate the Hugging
    Face cache. Users who explicitly want standard Transformers download behavior
    can instantiate this class directly with ``local_files_only=False``.
    """

    def __init__(
        self,
        model_id: str = DEFAULT_TRANSFORMERS_MODEL,
        cache_path: str | Path = cache.DEFAULT_CACHE_PATH,
        refresh_cache: bool = False,
        *,
        local_files_only: bool | None = None,
        max_input_tokens: int = 4096,
        max_new_tokens: int = 2048,
        device: str | None = None,
    ) -> None:
        self.model_id = model_id or DEFAULT_TRANSFORMERS_MODEL
        self.name = "transformers:" + self.model_id
        self.cache_path = Path(cache_path)
        self.refresh_cache = refresh_cache
        self.local_files_only = _local_files_only_default(local_files_only)
        self.max_input_tokens = int(max_input_tokens)
        self.max_new_tokens = int(max_new_tokens)
        self.device = device
        self.last_cache_hit = False
        self._tokenizer: Any | None = None
        self._model: Any | None = None
        self._is_encoder_decoder = False

    def propose_plan(self, schema: Any, hints: dict | None = None) -> GenerationPlan:
        input_payload = {
            "schema": canonical_schema(schema),
            "hints": canonical_json(hints or {}),
        }
        prompt = render_prompt(
            "propose_plan_v1.txt",
            {"schema_json": input_payload["schema"], "hints_json": input_payload["hints"]},
        )
        payload = self._cached_json_call("propose_plan_v1", input_payload, prompt)
        return plan_from_advisor_payload(
            payload,
            schema=schema,
            advisor=self.name,
            model_id=self.model_id,
        )

    def tag_columns(self, schema: Any, samples: dict[str, list] | None = None) -> Any:
        input_payload = {
            "schema": canonical_schema(schema),
            "samples": canonical_json(samples or {}),
        }
        prompt = render_prompt(
            "tag_columns_v1.txt",
            {"schema_json": input_payload["schema"], "samples_json": input_payload["samples"]},
        )
        payload = self._cached_json_call("tag_columns_v1", input_payload, prompt)
        return tags_from_advisor_payload(
            payload,
            schema=schema,
            advisor=self.name,
            model_id=self.model_id,
        )

    def review_sample(
        self,
        data: dict,
        plan: GenerationPlan,
        sample_size: int = 500,
    ) -> Any:
        input_payload = {
            "data": canonical_json(data),
            "plan": plan.to_dict(),
            "sample_size": int(sample_size),
        }
        prompt = render_prompt(
            "review_sample_v1.txt",
            {
                "data_json": input_payload["data"],
                "plan_json": input_payload["plan"],
                "sample_size": input_payload["sample_size"],
            },
        )
        payload = self._cached_json_call("review_sample_v1", input_payload, prompt)
        return report_from_advisor_payload(
            payload,
            advisor=self.name,
            model_id=self.model_id,
            sample_size=sample_size,
        )

    def _cached_json_call(
        self,
        prompt_version: str,
        input_payload: dict[str, Any],
        prompt: str,
    ) -> dict[str, Any]:
        key, input_hash = cache.make_cache_key(
            self.name,
            self.model_id,
            prompt_version,
            input_payload,
        )
        if not self.refresh_cache:
            entry = cache.get(key, self.cache_path, advisor=self.name)
            if entry is not None:
                self.last_cache_hit = True
                return dict(entry.get("response", {}))
        self.last_cache_hit = False
        raw = self._call_model(prompt)
        try:
            payload = parse_json_object(raw)
        except AdvisorResponseError:
            stricter_prompt = (
                prompt
                + "\nReturn exactly one valid JSON object. Do not include markdown, prose, or code fences."
            )
            raw = self._call_model(stricter_prompt)
            payload = parse_json_object(raw)
        cache.put(
            key,
            {
                "cache_key": key,
                "advisor": self.name,
                "model_id": self.model_id,
                "prompt_version": prompt_version,
                "input_hash": input_hash,
                "response": payload,
            },
            self.cache_path,
            advisor=self.name,
        )
        return payload

    def _call_model(self, prompt: str) -> str:
        tokenizer, model = self._load_model()
        full_prompt = SYSTEM_PROMPT + "\n\n" + prompt
        inputs = tokenizer(
            full_prompt,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_input_tokens,
        )
        if self.device and hasattr(inputs, "to"):
            inputs = inputs.to(self.device)
        outputs = model.generate(
            **inputs,
            max_new_tokens=self.max_new_tokens,
            do_sample=False,
        )
        output = outputs[0] if isinstance(outputs, (list, tuple)) else outputs[0]
        text = tokenizer.decode(output, skip_special_tokens=True).strip()
        if not self._is_encoder_decoder and text.startswith(full_prompt):
            text = text[len(full_prompt) :].strip()
        if not text:
            raise AdvisorResponseError("Transformers advisor returned an empty response.")
        return text

    def _load_model(self) -> tuple[Any, Any]:
        if self._tokenizer is not None and self._model is not None:
            return self._tokenizer, self._model
        try:
            from transformers import (
                AutoConfig,
                AutoModelForCausalLM,
                AutoModelForSeq2SeqLM,
                AutoTokenizer,
            )
        except ImportError as exc:
            raise AdvisorUnavailableError(OPTIONAL_DEPENDENCY_MESSAGE) from exc

        try:
            config = AutoConfig.from_pretrained(
                self.model_id,
                local_files_only=self.local_files_only,
                trust_remote_code=False,
            )
            self._is_encoder_decoder = bool(getattr(config, "is_encoder_decoder", False))
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_id,
                local_files_only=self.local_files_only,
                trust_remote_code=False,
            )
            model_cls = AutoModelForSeq2SeqLM if self._is_encoder_decoder else AutoModelForCausalLM
            self._model = model_cls.from_pretrained(
                self.model_id,
                local_files_only=self.local_files_only,
                trust_remote_code=False,
            )
        except OSError as exc:
            raise AdvisorUnavailableError(
                "Could not load the requested Transformers model locally. Use a local model path, "
                "pre-download the model into the Hugging Face cache, or instantiate "
                "TransformersAdvisor(local_files_only=False) explicitly if downloads are acceptable "
                "for your environment."
            ) from exc
        if self.device and hasattr(self._model, "to"):
            self._model = self._model.to(self.device)
        if hasattr(self._model, "eval"):
            self._model.eval()
        return self._tokenizer, self._model


def _local_files_only_default(value: bool | None) -> bool:
    if value is not None:
        return bool(value)
    env_value = os.getenv("GREAT_GENERATOR_TRANSFORMERS_LOCAL_FILES_ONLY")
    if env_value is None:
        return True
    return env_value.strip().lower() not in {"0", "false", "no", "off"}
