"""vLLM OpenAI client. response_format JSON schema. Never tools=."""

from __future__ import annotations

import json
import time
from typing import Any, Protocol

from app.agent.schema import RESPONSE_FORMAT
from app.settings import Settings, get_settings

_BRAIN_RETRIES = 4
_RETRY_STATUSES = frozenset({429, 503})


class Brain(Protocol):
    def complete(self, messages: list[dict[str, Any]]) -> str:
        """Return the model's JSON text."""


class UnconfiguredBrain:
    """BRAIN=fake with no test script. complete() is a 503, constructing is not."""

    def complete(self, messages: list[dict[str, Any]]) -> str:
        raise RuntimeError("BRAIN=fake has no script; tests must inject FakeBrain")


class FakeBrain:
    """Canned JSON for tests. No GPU."""

    def __init__(self, script: list[dict[str, Any]]) -> None:
        self.script = list(script)
        self.calls: list[list[dict[str, Any]]] = []

    def complete(self, messages: list[dict[str, Any]]) -> str:
        self.calls.append(list(messages))
        if not self.script:
            raise RuntimeError("FakeBrain has no more actions")
        return json.dumps(self.script.pop(0))


class VllmBrain:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.vllm_base_url:
            raise RuntimeError("VLLM_BASE_URL is not set")
        from openai import OpenAI

        self._client = OpenAI(
            base_url=self.settings.vllm_base_url.rstrip("/"),
            api_key=self.settings.vllm_api_key,
        )
        self._model = self.settings.vllm_model

    def complete(self, messages: list[dict[str, Any]]) -> str:
        last: BaseException | None = None
        for attempt in range(_BRAIN_RETRIES):
            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    response_format=RESPONSE_FORMAT,
                    max_tokens=512,
                )
                content = response.choices[0].message.content
                if not content:
                    raise RuntimeError("vLLM returned an empty completion")
                return content
            except Exception as exc:
                last = exc
                code = getattr(exc, "status_code", None)
                if code in _RETRY_STATUSES and attempt < _BRAIN_RETRIES - 1:
                    time.sleep(2 * (2**attempt))
                    continue
                if isinstance(code, int) and code >= 500:
                    raise RuntimeError(f"brain GPU returned HTTP {code}") from exc
                msg = str(exc)
                if code == 400 and "maximum context length" in msg:
                    raise RuntimeError(
                        "brain prompt was too long; try a shorter look or listen window"
                    ) from exc
                raise
        raise RuntimeError("brain GPU unavailable") from last


def build_brain(settings: Settings | None = None) -> Brain:
    cfg = settings or get_settings()
    if cfg.brain == "vllm":
        return VllmBrain(cfg)
    if cfg.brain == "fake":
        return UnconfiguredBrain()
    raise RuntimeError(f"unknown BRAIN={cfg.brain}")
