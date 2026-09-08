"""Laptop-owned look / listen / answer loop. Caps stay in Phase 2 scissors."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.agent.client import Brain
from app.agent.parts import listen_message, look_message, refuse_message
from app.agent.schema import (
    MAX_ROUNDS,
    RETRY_PROMPT,
    SYSTEM_PROMPT,
    BrainAction,
    BrainParseError,
    parse_action,
)
from app.tools import ScissorsError, get_audio, get_frames, get_meta
from app.tools.meta import VideoMeta


class LoopError(Exception):
    """The loop stopped without an answer."""


@dataclass
class Step:
    do: str
    start_s: float | None = None
    end_s: float | None = None
    ok: bool = True
    detail: str = ""


@dataclass
class LoopResult:
    answer: str
    citations: list[float]
    steps: list[Step] = field(default_factory=list)


def _window(action: BrainAction) -> tuple[float, float]:
    if action.start_s is None or action.end_s is None:
        raise ScissorsError("look/listen need start_s and end_s")
    return action.start_s, action.end_s


def _ask(brain: Brain, messages: list[dict[str, Any]]) -> BrainAction:
    raw = brain.complete(messages)
    try:
        return parse_action(raw)
    except BrainParseError:
        messages.append({"role": "user", "content": RETRY_PROMPT})
        raw = brain.complete(messages)
        return parse_action(raw)


def run_loop(path: str | Path, question: str, brain: Brain) -> LoopResult:
    meta: VideoMeta = get_meta(path)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Video duration {meta.duration_s:.3f}s. "
                f"has_video={meta.has_video} has_audio={meta.has_audio}. "
                f"Question: {question}"
            ),
        },
    ]
    steps: list[Step] = []
    rounds = 0

    while True:
        if rounds >= MAX_ROUNDS:
            raise LoopError(f"stopped after {MAX_ROUNDS} look/listen rounds")
        try:
            action = _ask(brain, messages)
        except BrainParseError as exc:
            raise LoopError("model did not return look/listen/answer JSON") from exc
        messages.append(
            {"role": "assistant", "content": action.model_dump_json()},
        )

        if action.do == "answer":
            text = (action.answer or "").strip()
            if not text:
                raise LoopError("answer JSON had an empty answer")
            steps.append(Step(do="answer", detail=text, ok=True))
            return LoopResult(answer=text, citations=list(action.times), steps=steps)

        rounds += 1
        try:
            start_s, end_s = _window(action)
            if action.do == "look":
                frames = get_frames(path, start_s, end_s, fps=action.fps)
                shown = [frame.t for frame in frames]
                messages.append(look_message(frames))
                steps.append(
                    Step(
                        do="look",
                        start_s=start_s,
                        end_s=end_s,
                        ok=True,
                        detail=",".join(f"{t:.2f}" for t in shown),
                    )
                )
            else:
                wav = get_audio(path, start_s, end_s)
                messages.append(listen_message(start_s, end_s, wav))
                steps.append(
                    Step(
                        do="listen",
                        start_s=start_s,
                        end_s=end_s,
                        ok=True,
                        detail="audio",
                    )
                )
        except ScissorsError as exc:
            messages.append(refuse_message(str(exc)))
            steps.append(
                Step(
                    do=action.do,
                    start_s=action.start_s,
                    end_s=action.end_s,
                    ok=False,
                    detail=str(exc),
                )
            )
