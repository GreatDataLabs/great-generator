"""OpenAI advisor stub."""

from __future__ import annotations


class OpenAIAdvisor:
    """Placeholder for a future OpenAI advisor."""

    def __init__(self, model_id: str = "gpt-4o-mini", **_: object) -> None:
        self.model_id = model_id
        self.name = "openai:" + model_id

    def propose_plan(self, *args: object, **kwargs: object) -> object:
        raise NotImplementedError(
            "OpenAI advisor support is planned. Track progress at "
            "https://github.com/GreatDataLabs/great-generator/issues."
        )

    def tag_columns(self, *args: object, **kwargs: object) -> object:
        raise NotImplementedError(
            "OpenAI advisor support is planned. Track progress at "
            "https://github.com/GreatDataLabs/great-generator/issues."
        )

    def review_sample(self, *args: object, **kwargs: object) -> object:
        raise NotImplementedError(
            "OpenAI advisor support is planned. Track progress at "
            "https://github.com/GreatDataLabs/great-generator/issues."
        )
