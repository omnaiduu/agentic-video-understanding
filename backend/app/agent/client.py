"""vLLM OpenAI client. response_format JSON schema. Never tools=."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Protocol

from app.agent.schema import RESPONSE_FORMAT
from app.settings import Settings, get_settings

_BRAIN_RETRIES = 4
_RETRY_STATUSES = frozenset({429, 503})
_THINKING_MAX_TOKENS = 4096
_DEFAULT_MAX_TOKENS = 512


@dataclass(frozen=True)
class BrainTurn:
    """JSON move in content. Thoughts stay out of the next prompt."""

    content: str
    reasoning: str | None = None


class Brain(Protocol):
    def complete(self, messages: list[dict[str, Any]]) -> str | BrainTurn:
        """Return the model's JSON text, optionally with reasoning."""


class UnconfiguredBrain:
    """BRAIN=fake with no test script. complete() is a 503, constructing is not."""

    def complete(self, messages: list[dict[str, Any]]) -> str:
        raise RuntimeError("BRAIN=fake has no script; tests must inject FakeBrain")


class FakeBrain:
    """Canned JSON for tests. No GPU."""

    def __init__(
        self,
        script: list[dict[str, Any]],
        reasonings: list[str | None] | None = None,
    ) -> None:
        self.script = list(script)
        self.reasonings = None if reasonings is None else list(reasonings)
        self.calls: list[list[dict[str, Any]]] = []

    def complete(self, messages: list[dict[str, Any]]) -> str | BrainTurn:
        self.calls.append(list(messages))
        if not self.script:
            raise RuntimeError("FakeBrain has no more actions")
        content = json.dumps(self.script.pop(0))
        if self.reasonings is None:
            return content
        reasoning = self.reasonings.pop(0) if self.reasonings else None
        return BrainTurn(content=content, reasoning=reasoning)


def as_turn(raw: str | BrainTurn) -> BrainTurn:
    if isinstance(raw, BrainTurn):
        return raw
    return BrainTurn(content=raw)


def _message_reasoning(message: Any) -> str | None:
    for key in ("reasoning", "reasoning_content"):
        value = getattr(message, key, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    extra = getattr(message, "model_extra", None)
    if isinstance(extra, dict):
        for key in ("reasoning", "reasoning_content"):
            value = extra.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


class VllmBrain:
    def __init__(self, settings: Settings | None = None, *, thinking: bool = False) -> None:
        self.settings = settings or get_settings()
        self.thinking = thinking
        base = (
            self.settings.vllm_thinking_base_url
            if thinking
            else self.settings.vllm_base_url
        )
        if not base:
            raise RuntimeError(
                "VLLM_THINKING_BASE_URL is not set"
                if thinking
                else "VLLM_BASE_URL is not set"
            )
        from openai import OpenAI

        self._client = OpenAI(
            base_url=base.rstrip("/"),
            api_key=self.settings.vllm_api_key,
        )
        self._model = self.settings.vllm_model

    def complete(self, messages: list[dict[str, Any]]) -> BrainTurn:
        last: BaseException | None = None
        for attempt in range(_BRAIN_RETRIES):
            try:
                kwargs: dict[str, Any] = {
                    "model": self._model,
                    "messages": messages,
                    "response_format": RESPONSE_FORMAT,
                    "max_tokens": (
                        _THINKING_MAX_TOKENS if self.thinking else _DEFAULT_MAX_TOKENS
                    ),
                }
                if self.thinking:
                    kwargs["extra_body"] = {
                        "chat_template_kwargs": {"enable_thinking": True}
                    }
                response = self._client.chat.completions.create(**kwargs)
                message = response.choices[0].message
                content = message.content
                if not content:
                    raise RuntimeError("vLLM returned an empty completion")
                return BrainTurn(content=content, reasoning=_message_reasoning(message))
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


def build_brain(settings: Settings | None = None, *, thinking: bool = False) -> Brain:
    cfg = settings or get_settings()
    if cfg.brain == "vllm":
        return VllmBrain(cfg, thinking=thinking)
    if cfg.brain == "fake":
        return UnconfiguredBrain()
    raise RuntimeError(f"unknown BRAIN={cfg.brain}")
