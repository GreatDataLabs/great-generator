"""llama.cpp advisor stub."""

from __future__ import annotations


class LlamaCppAdvisor:
    """Placeholder for a future llama.cpp advisor."""

    def __init__(self, model_id: str, **_: object) -> None:
        self.model_id = model_id
        self.name = "llamacpp:" + model_id

    def propose_plan(self, *args: object, **kwargs: object) -> object:
        raise NotImplementedError(
            "llama.cpp advisor support is planned. Track progress at "
            "https://github.com/GreatDataLabs/great-generator/issues."
        )

    def tag_columns(self, *args: object, **kwargs: object) -> object:
        raise NotImplementedError(
            "llama.cpp advisor support is planned. Track progress at "
            "https://github.com/GreatDataLabs/great-generator/issues."
        )

    def review_sample(self, *args: object, **kwargs: object) -> object:
        raise NotImplementedError(
            "llama.cpp advisor support is planned. Track progress at "
            "https://github.com/GreatDataLabs/great-generator/issues."
        )
