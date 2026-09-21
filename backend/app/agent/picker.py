"""System One picker: score a closed set of search-book letters, skip JSON decode.

The JSON brain still looks, listens, exports, and writes answers. This module
only chooses which phone book to open on the first text-only hop.

Default is off. FakePicker is for tests. LogitPicker reads vLLM logprobs.
"""

from __future__ import annotations

import math
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.agent.schema import DoKind
from app.models import IndexStatus
from app.settings import Settings, get_settings

DEFAULT_MIN_P = 0.55
MISSING_LOGIT = -100.0
SEARCH_DOS: frozenset[str] = frozenset(
    {"search", "search_visual", "search_audio", "search_slides"}
)
_MEDIA_TYPES = frozenset({"image_url", "input_audio", "input_image", "audio_url"})
_LETTERS = "ABCDEFGHIJ"
_PICKER_RETRIES = 2
_RETRY_STATUSES = frozenset({429, 503})
_TOP_LOGPROBS = 20

PICKER_SYSTEM = (
    "You route one question about a video to the first index to open. "
    "Reply with exactly one letter. No JSON. No explanation. "
    "Do not look, listen, export, or answer."
)

_BOOKS: tuple[tuple[str, str, str], ...] = (
    ("search", "Spoken words (what people said)", "transcript"),
    (
        "search_visual",
        "Pictures (silent visual: color, objects, motion)",
        "visual",
    ),
    (
        "search_audio",
        "Sounds (tones, music, effects — not the meaning of speech)",
        "audio",
    ),
    (
        "search_slides",
        "On-screen slides (printed headings and numbers)",
        "slides",
    ),
)


@dataclass(frozen=True)
class PickerOption:
    letter: str
    do: str | None
    label: str

    @property
    def key(self) -> str:
        return self.do if self.do is not None else "abstain"


@dataclass
class PickerDecision:
    letter: str = ""
    do: str | None = None
    p_max: float = 0.0
    probs: dict[str, float] = field(default_factory=dict)
    used: bool = False
    reason: str = ""


class Picker(Protocol):
    shadow: bool

    def score(
        self,
        question: str,
        options: Sequence[PickerOption],
        *,
        context: str = "",
    ) -> PickerDecision:
        """Return letter probabilities. The loop decides whether to commit."""


def softmax(logits: Sequence[float]) -> list[float]:
    if not logits:
        return []
    peak = max(logits)
    shifted = [math.exp(value - peak) for value in logits]
    total = sum(shifted)
    if total <= 0.0 or not math.isfinite(total):
        n = len(logits)
        return [1.0 / n] * n
    return [value / total for value in shifted]


def normalize_letter_token(token: str) -> str:
    text = (
        (token or "")
        .replace("▁", " ")
        .replace("Ġ", " ")
        .replace("Ċ", " ")
        .strip()
    )
    text = text.strip("()[].:|-")
    if not text:
        return ""
    first = text[0]
    if first.isalpha():
        return first.upper()
    return ""


def letter_logits(
    top_logprobs: Sequence[tuple[str, float]],
    letters: Sequence[str],
) -> dict[str, float]:
    best: dict[str, float] = {}
    wanted = {letter.upper() for letter in letters}
    for token, logprob in top_logprobs:
        letter = normalize_letter_token(token)
        if letter not in wanted:
            continue
        previous = best.get(letter)
        if previous is None or logprob > previous:
            best[letter] = float(logprob)
    return {letter: best.get(letter, MISSING_LOGIT) for letter in letters}


def last_user_is_text(messages: Sequence[dict[str, Any]]) -> bool:
    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str) or content is None:
            return True
        if not isinstance(content, list):
            return True
        for part in content:
            if isinstance(part, dict) and part.get("type") in _MEDIA_TYPES:
                return False
        return True
    return True


def routing_options(
    *,
    transcript_status: str,
    visual_status: str,
    audio_status: str,
    slides_status: str,
) -> list[PickerOption]:
    ready = {
        "transcript": transcript_status == IndexStatus.ready.value,
        "visual": visual_status == IndexStatus.ready.value,
        "audio": audio_status == IndexStatus.ready.value,
        "slides": slides_status == IndexStatus.ready.value,
    }
    options: list[PickerOption] = []
    index = 0
    for do, label, book in _BOOKS:
        if not ready[book]:
            continue
        options.append(PickerOption(letter=_LETTERS[index], do=do, label=label))
        index += 1
    options.append(
        PickerOption(
            letter=_LETTERS[index],
            do=None,
            label=(
                "None of these indexes. A time is already known, "
                "or Gemma should look, listen, or answer."
            ),
        )
    )
    return options


def picker_prompt(question: str, options: Sequence[PickerOption], context: str) -> str:
    lines = [
        f"Question: {question.strip()}",
        "",
        "Indexes:",
    ]
    for option in options:
        lines.append(f"{option.letter}. {option.label}")
    if context.strip():
        lines.extend(["", context.strip()])
    lines.extend(["", "Letter:"])
    return "\n".join(lines)


def decide_picker(
    score: PickerDecision,
    *,
    min_p: float = DEFAULT_MIN_P,
    shadow: bool = False,
) -> PickerDecision:
    reason = score.reason or "scored"
    used = False
    if shadow:
        reason = "shadow"
    elif score.do not in SEARCH_DOS:
        reason = "abstain" if score.do is None else "not_search"
    elif not score.letter:
        reason = "unknown_option"
    elif score.p_max < min_p:
        reason = "low_confidence"
    else:
        used = True
        reason = "commit"
    return PickerDecision(
        letter=score.letter,
        do=score.do,
        p_max=score.p_max,
        probs=dict(score.probs),
        used=used,
        reason=reason,
    )


def picker_allowed(
    *,
    picker: Picker | None,
    steps: Sequence[Any],
    last_times: Sequence[Any] | None,
    force_answer: bool,
    messages: Sequence[dict[str, Any]],
    thinking_brain: bool,
    already_tried: bool,
) -> bool:
    if picker is None or already_tried or force_answer or thinking_brain:
        return False
    if steps:
        return False
    if last_times:
        return False
    return last_user_is_text(messages)


def _probs_from_logits(
    options: Sequence[PickerOption],
    logits: dict[str, float],
) -> PickerDecision:
    letters = [option.letter for option in options]
    ordered = [logits.get(letter, MISSING_LOGIT) for letter in letters]
    probs = softmax(ordered)
    mapping = {option.key: prob for option, prob in zip(options, probs, strict=True)}
    if not options:
        return PickerDecision(reason="no_options")
    best_index = max(range(len(probs)), key=lambda i: probs[i])
    best = options[best_index]
    return PickerDecision(
        letter=best.letter,
        do=best.do,
        p_max=probs[best_index],
        probs=mapping,
        used=False,
        reason="scored",
    )


class FakePicker:
    """Canned first-hop choice for tests. No GPU."""

    def __init__(
        self,
        script: list[str | None],
        *,
        p_max: float = 0.9,
        shadow: bool = False,
        probs: dict[str, float] | None = None,
    ) -> None:
        self.script = list(script)
        self.p_max = p_max
        self.shadow = shadow
        self.probs = dict(probs or {})
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def score(
        self,
        question: str,
        options: Sequence[PickerOption],
        *,
        context: str = "",
    ) -> PickerDecision:
        del context
        keys = tuple(option.key for option in options)
        self.calls.append((question, keys))
        if not self.script:
            raise RuntimeError("FakePicker has no more choices")
        raw = self.script.pop(0)
        if raw in (None, "", "abstain"):
            chosen = next((option for option in options if option.do is None), None)
        else:
            chosen = next((option for option in options if option.do == raw), None)
        if chosen is None:
            return PickerDecision(
                letter="",
                do=raw if isinstance(raw, str) else None,
                p_max=self.p_max,
                probs=dict(self.probs),
                reason="unknown_option",
            )
        probs = dict(self.probs)
        if chosen.key not in probs:
            rest = [option.key for option in options if option.key != chosen.key]
            leftover = max(0.0, 1.0 - self.p_max)
            each = leftover / len(rest) if rest else 0.0
            probs[chosen.key] = self.p_max
            for key in rest:
                probs.setdefault(key, each)
        return PickerDecision(
            letter=chosen.letter,
            do=chosen.do,
            p_max=self.p_max,
            probs=probs,
            reason="scored",
        )


def _top_logprobs(response: Any) -> list[tuple[str, float]]:
    choice = response.choices[0]
    logprobs = getattr(choice, "logprobs", None)
    if logprobs is None:
        return []
    content = getattr(logprobs, "content", None) or []
    if not content:
        return []
    first = content[0]
    out: list[tuple[str, float]] = []
    token = getattr(first, "token", None)
    logprob = getattr(first, "logprob", None)
    if isinstance(token, str) and isinstance(logprob, (int, float)):
        out.append((token, float(logprob)))
    for item in getattr(first, "top_logprobs", None) or []:
        item_token = getattr(item, "token", None)
        item_logprob = getattr(item, "logprob", None)
        if isinstance(item_token, str) and isinstance(item_logprob, (int, float)):
            out.append((item_token, float(item_logprob)))
    return out


class LogitPicker:
    """One-token vLLM pass. Read letter logprobs. Do not fill the JSON form."""

    def __init__(self, settings: Settings | None = None, *, shadow: bool = False) -> None:
        self.settings = settings or get_settings()
        self.shadow = shadow
        base = self.settings.vllm_base_url
        if not base:
            raise RuntimeError("VLLM_BASE_URL is not set")
        from openai import OpenAI

        self._client = OpenAI(
            base_url=base.rstrip("/"),
            api_key=self.settings.vllm_api_key,
        )
        self._model = self.settings.vllm_model

    def score(
        self,
        question: str,
        options: Sequence[PickerOption],
        *,
        context: str = "",
    ) -> PickerDecision:
        if not options:
            return PickerDecision(reason="no_options")
        messages = [
            {"role": "system", "content": PICKER_SYSTEM},
            {
                "role": "user",
                "content": picker_prompt(question, options, context),
            },
        ]
        last: BaseException | None = None
        for attempt in range(_PICKER_RETRIES):
            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    max_tokens=1,
                    temperature=0,
                    logprobs=True,
                    top_logprobs=_TOP_LOGPROBS,
                )
                pairs = _top_logprobs(response)
                if not pairs:
                    return PickerDecision(reason="no_logprobs")
                letters = [option.letter for option in options]
                logits = letter_logits(pairs, letters)
                return _probs_from_logits(options, logits)
            except Exception as exc:
                last = exc
                code = getattr(exc, "status_code", None)
                if code in _RETRY_STATUSES and attempt < _PICKER_RETRIES - 1:
                    time.sleep(2 * (2**attempt))
                    continue
                raise RuntimeError("picker GPU unavailable") from last
        raise RuntimeError("picker GPU unavailable") from last


def build_picker(settings: Settings | None = None) -> Picker | None:
    cfg = settings or get_settings()
    mode = (cfg.picker or "off").strip().lower()
    if mode in {"off", "", "none"}:
        return None
    if mode == "fake":
        return None
    if mode == "logit":
        return LogitPicker(cfg, shadow=False)
    if mode == "shadow":
        return LogitPicker(cfg, shadow=True)
    raise RuntimeError(f"unknown PICKER={cfg.picker}")


def as_search_do(value: str | None) -> DoKind | None:
    if value in SEARCH_DOS:
        return value  # type: ignore[return-value]
    return None
