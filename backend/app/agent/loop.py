"""Laptop-owned look / listen / search / search_visual / search_audio / search_slides / export / answer loop."""

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
    speech_already_searched_message,
    slide_search_message,
    slides_not_ready_message,
    strip_input_audio,
    transcript_not_ready_message,
    visual_not_ready_message,
    visual_search_message,
)
from app.agent.memory import memory_text
from app.agent.schema import (
    FORCE_ANSWER_PROMPT,
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
from app.search.slides import SlideHit
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
SlideSearchFn = Callable[[str], list[SlideHit]]
ExportFn = Callable[[float, float], ExportResult]


def _window(action: BrainAction) -> tuple[float, float]:
    if action.start_s is None or action.end_s is None:
        raise ScissorsError("look/listen/export need start_s and end_s")
    return action.start_s, action.end_s


def _citations_from_steps(steps: list[Step]) -> list[float]:
    for step in reversed(steps):
        if not step.ok:
            continue
        if step.start_s is None:
            continue
        times = [step.start_s]
        if step.end_s is not None and step.end_s != step.start_s:
            times.append(step.end_s)
        return times
    return []


def _forced_answer(
    question: str,
    steps: list[Step],
    export_url: str | None,
) -> LoopResult:
    bits: list[str] = []
    for step in steps:
        if not step.ok:
            bits.append(f"{step.do} failed: {step.detail}")
            continue
        window = ""
        if step.start_s is not None and step.end_s is not None:
            window = f" {step.start_s:.2f}s–{step.end_s:.2f}s"
        detail = f" — {step.detail}" if step.detail else ""
        bits.append(f"{step.do}{window}{detail}")
    if bits:
        text = (
            "I used my last look/listen/search moves. Here is what I already found:\n"
            + "\n".join(bits)
        )
    else:
        text = (
            f"I could not finish answering {question!r}. "
            "Try a shorter look window or a simpler question."
        )
    steps.append(Step(do="answer", detail=text, ok=True))
    return LoopResult(
        answer=text,
        citations=_citations_from_steps(steps),
        steps=steps,
        export_url=export_url,
    )


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
    search_slides: SlideSearchFn | None = None,
    export_clip: ExportFn | None = None,
    export_audio: ExportFn | None = None,
    transcript_status: str | None = None,
    visual_status: str | None = None,
    audio_status: str | None = None,
    slides_status: str | None = None,
    history: list[tuple[str, str]] | None = None,
    last_times: list[dict] | None = None,
) -> LoopResult:
    meta: VideoMeta = get_meta(path)
    speech_status = transcript_status or IndexStatus.pending.value
    picture_status = visual_status or IndexStatus.pending.value
    sound_status = audio_status or IndexStatus.pending.value
    slide_status = slides_status or IndexStatus.pending.value
    opening = (
        f"Video duration {meta.duration_s:.3f}s. "
        f"has_video={meta.has_video} has_audio={meta.has_audio}. "
        f"transcript_status={speech_status}. "
        f"visual_status={picture_status}. "
        f"audio_status={sound_status}. "
        f"slides_status={slide_status}."
    )
    remembered = memory_text(history, last_times)
    question_line = f"Question: {question}"
    user_text = (
        f"{opening}\n{remembered}\n{question_line}" if remembered else f"{opening} {question_line}"
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]
    steps: list[Step] = []
    last_export_url: str | None = None
    rounds = 0
    searched_speech = False

    while True:
        if rounds >= MAX_ROUNDS:
            messages.append({"role": "user", "content": FORCE_ANSWER_PROMPT})
            try:
                action = _ask(brain, messages)
            except (BrainParseError, RuntimeError):
                return _forced_answer(question, steps, last_export_url)
            if action.do == "answer":
                text = (action.answer or "").strip()
                if text:
                    steps.append(Step(do="answer", detail=text, ok=True))
                    return LoopResult(
                        answer=text,
                        citations=list(action.times),
                        steps=steps,
                        export_url=last_export_url,
                    )
            return _forced_answer(question, steps, last_export_url)
        try:
            action = _ask(brain, messages)
        except BrainParseError as exc:
            if steps:
                return _forced_answer(question, steps, last_export_url)
            raise LoopError(
                "model did not return look/listen/search/search_visual/search_audio/search_slides/export/answer JSON"
            ) from exc
        messages.append(
            {"role": "assistant", "content": action.model_dump_json()},
        )

        if action.do == "answer":
            text = (action.answer or "").strip()
            if not text:
                if steps:
                    return _forced_answer(question, steps, last_export_url)
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
            if searched_speech:
                messages.append(speech_already_searched_message())
                steps.append(
                    Step(do="search", ok=False, detail="already searched spoken words")
                )
                continue
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
            searched_speech = True
            messages.append(search_message(hits, query))
            shown = ",".join(f"{hit.t:.2f}" for hit in hits)
            first = hits[0] if hits else None
            steps.append(
                Step(
                    do="search",
                    start_s=first.t if first is not None else None,
                    end_s=first.t if first is not None else None,
                    ok=True,
                    detail=f"{query}: {shown}" if shown else query,
                )
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
            first = hits[0] if hits else None
            steps.append(
                Step(
                    do="search_visual",
                    start_s=first.t if first is not None else None,
                    end_s=first.t if first is not None else None,
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
            first = hits[0] if hits else None
            steps.append(
                Step(
                    do="search_audio",
                    start_s=first.start_s if first is not None else None,
                    end_s=first.end_s if first is not None else None,
                    ok=True,
                    detail=f"{query}: {shown}" if shown else query,
                )
            )
            continue

        if action.do == "search_slides":
            query = (action.query or question).strip()
            if slide_status != IndexStatus.ready.value:
                messages.append(slides_not_ready_message(slide_status))
                steps.append(
                    Step(
                        do="search_slides",
                        ok=False,
                        detail=f"slides {slide_status}",
                    )
                )
                continue
            if search_slides is None:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "search_slides is not wired. Use look, listen, or answer."
                        ),
                    }
                )
                steps.append(
                    Step(do="search_slides", ok=False, detail="search_slides not wired")
                )
                continue
            hits = search_slides(query)[:8]
            messages.append(slide_search_message(hits, query))
            shown = ",".join(f"{hit.t:.2f}" for hit in hits)
            first = hits[0] if hits else None
            steps.append(
                Step(
                    do="search_slides",
                    start_s=first.t if first is not None else None,
                    end_s=first.t_end if first is not None else None,
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
                strip_input_audio(messages)
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
