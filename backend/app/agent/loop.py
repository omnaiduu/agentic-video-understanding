"""Laptop-owned look / listen / search / search_visual / search_audio / export / answer loop."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.agent.client import Brain
from app.agent.parts import (
    audio_not_ready_message,
    audio_search_message,
    export_message,
    listen_message,
    look_message,
    refuse_message,
    search_message,
    transcript_not_ready_message,
    visual_not_ready_message,
    visual_search_message,
)
from app.agent.schema import (
    MAX_ROUNDS,
    RETRY_PROMPT,
    SYSTEM_PROMPT,
    BrainAction,
    BrainParseError,
    parse_action,
)
from app.models import IndexStatus
from app.search.audio import AudioSearchResult
from app.search.transcript import TranscriptHit
from app.search.visual import VisualHit
from app.tools import ScissorsError, get_audio, get_frames, get_meta
from app.tools.export import ExportResult
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
    export_url: str | None = None


SearchFn = Callable[[str], list[TranscriptHit]]
VisualSearchFn = Callable[[str], list[VisualHit]]
AudioSearchFn = Callable[[str], AudioSearchResult]
ExportFn = Callable[[float, float], ExportResult]


def _window(action: BrainAction) -> tuple[float, float]:
    if action.start_s is None or action.end_s is None:
        raise ScissorsError("look/listen/export need start_s and end_s")
    return action.start_s, action.end_s


def _ask(brain: Brain, messages: list[dict[str, Any]]) -> BrainAction:
    raw = brain.complete(messages)
    try:
        return parse_action(raw)
    except BrainParseError:
        messages.append({"role": "user", "content": RETRY_PROMPT})
        raw = brain.complete(messages)
        return parse_action(raw)


def run_loop(
    path: str | Path,
    question: str,
    brain: Brain,
    *,
    search: SearchFn | None = None,
    search_visual: VisualSearchFn | None = None,
    search_audio: AudioSearchFn | None = None,
    export_clip: ExportFn | None = None,
    export_audio: ExportFn | None = None,
    transcript_status: str | None = None,
    visual_status: str | None = None,
    audio_status: str | None = None,
) -> LoopResult:
    meta: VideoMeta = get_meta(path)
    speech_status = transcript_status or IndexStatus.pending.value
    picture_status = visual_status or IndexStatus.pending.value
    sound_status = audio_status or IndexStatus.pending.value
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Video duration {meta.duration_s:.3f}s. "
                f"has_video={meta.has_video} has_audio={meta.has_audio}. "
                f"transcript_status={speech_status}. "
                f"visual_status={picture_status}. "
                f"audio_status={sound_status}. "
                f"Question: {question}"
            ),
        },
    ]
    steps: list[Step] = []
    last_export_url: str | None = None
    rounds = 0

    while True:
        if rounds >= MAX_ROUNDS:
            raise LoopError(
                f"stopped after {MAX_ROUNDS} look/listen/search/search_visual/search_audio/export rounds"
            )
        try:
            action = _ask(brain, messages)
        except BrainParseError as exc:
            raise LoopError(
                "model did not return look/listen/search/search_visual/search_audio/export/answer JSON"
            ) from exc
        messages.append(
            {"role": "assistant", "content": action.model_dump_json()},
        )

        if action.do == "answer":
            text = (action.answer or "").strip()
            if not text:
                raise LoopError("answer JSON had an empty answer")
            steps.append(Step(do="answer", detail=text, ok=True))
            return LoopResult(
                answer=text,
                citations=list(action.times),
                steps=steps,
                export_url=last_export_url,
            )

        rounds += 1
        if action.do == "search":
            query = (action.query or question).strip()
            if speech_status != IndexStatus.ready.value:
                messages.append(transcript_not_ready_message(speech_status))
                steps.append(
                    Step(do="search", ok=False, detail=f"transcript {speech_status}")
                )
                continue
            if search is None:
                messages.append(
                    {
                        "role": "user",
                        "content": "search is not wired. Use look, listen, or answer.",
                    }
                )
                steps.append(Step(do="search", ok=False, detail="search not wired"))
                continue
            hits = search(query)[:8]
            messages.append(search_message(hits, query))
            shown = ",".join(f"{hit.t:.2f}" for hit in hits)
            steps.append(
                Step(do="search", ok=True, detail=f"{query}: {shown}" if shown else query)
            )
            continue

        if action.do == "search_visual":
            query = (action.query or question).strip()
            if picture_status != IndexStatus.ready.value:
                messages.append(visual_not_ready_message(picture_status))
                steps.append(
                    Step(
                        do="search_visual",
                        ok=False,
                        detail=f"visual {picture_status}",
                    )
                )
                continue
            if search_visual is None:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "search_visual is not wired. Use look, listen, or answer."
                        ),
                    }
                )
                steps.append(
                    Step(do="search_visual", ok=False, detail="search_visual not wired")
                )
                continue
            hits = search_visual(query)[:8]
            messages.append(visual_search_message(hits, query))
            shown = ",".join(f"{hit.t:.2f}" for hit in hits)
            steps.append(
                Step(
                    do="search_visual",
                    ok=True,
                    detail=f"{query}: {shown}" if shown else query,
                )
            )
            continue

        if action.do == "search_audio":
            query = (action.query or question).strip()
            if sound_status != IndexStatus.ready.value:
                messages.append(audio_not_ready_message(sound_status))
                steps.append(
                    Step(
                        do="search_audio",
                        ok=False,
                        detail=f"audio {sound_status}",
                    )
                )
                continue
            if search_audio is None:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "search_audio is not wired. Use look, listen, or answer."
                        ),
                    }
                )
                steps.append(
                    Step(do="search_audio", ok=False, detail="search_audio not wired")
                )
                continue
            result = search_audio(query)
            hits = result.hits[:8]
            messages.append(audio_search_message(result, query))
            shown = ",".join(f"{hit.start_s:.2f}" for hit in hits)
            steps.append(
                Step(
                    do="search_audio",
                    ok=True,
                    detail=f"{query}: {shown}" if shown else query,
                )
            )
            continue

        if action.do in ("export_clip", "export_audio"):
            fn = export_clip if action.do == "export_clip" else export_audio
            if fn is None:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"{action.do} is not wired. Use look, listen, or answer."
                        ),
                    }
                )
                steps.append(
                    Step(do=action.do, ok=False, detail=f"{action.do} not wired")
                )
                continue
            try:
                start_s, end_s = _window(action)
                result = fn(start_s, end_s)
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
                continue
            last_export_url = result.url
            messages.append(
                export_message(result.kind, result.start_s, result.end_s, result.url)
            )
            steps.append(
                Step(
                    do=action.do,
                    start_s=result.start_s,
                    end_s=result.end_s,
                    ok=True,
                    detail=result.url,
                )
            )
            continue

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
