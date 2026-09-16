"""Laptop skip-ahead stays. Recut / print-vs-speech bounces are gone.

Black mp4s, not the exam tape. Tests must not mention beep / clap / ship / $99
as answers. The OG sound path is search_audio → listen → export the heard range.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from app.agent.client import FakeBrain
from app.agent.loop import _is_next_step_after_listen, run_loop
from app.models import IndexStatus
from app.search.audio import AudioHit, AudioSearchResult
from app.search.transcript import TranscriptHit
from app.tools.export import ExportResult


def _act(do: str, **kwargs) -> dict:
    payload = {
        "do": do,
        "start_s": None,
        "end_s": None,
        "fps": None,
        "query": None,
        "answer": None,
        "times": [],
    }
    payload.update(kwargs)
    return payload


def _export(start_s: float, end_s: float) -> ExportResult:
    return ExportResult(
        id=uuid.uuid4(),
        kind="clip",
        start_s=start_s,
        end_s=end_s,
        path=Path("/tmp/clip.mp4"),
        url="/videos/x/exports/y",
    )


def _user_texts(brain: FakeBrain) -> list[str]:
    texts: list[str] = []
    for call in brain.calls:
        content = call[-1].get("content")
        if isinstance(content, str):
            texts.append(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    texts.append(str(part.get("text") or ""))
    return texts


EXAM_KEYS = (
    "beep",
    "ship the slide",
    "$99",
    "red alert",
    "q3 roadmap",
    "11.0s",
)


def test_loop_notes_are_not_an_exam_answer_key() -> None:
    root = Path(__file__).resolve().parents[1] / "app" / "agent"
    blob = (root / "loop.py").read_text() + (root / "parts.py").read_text()
    lowered = blob.lower()
    for key in EXAM_KEYS:
        assert key not in lowered, f"exam answer {key!r} leaked into laptop notes"


def test_skip_rule_needs_a_matching_look_and_listen() -> None:
    looked = [(0.0, 2.0)]
    listen = (0.0, 2.0)
    # 16s file, next 2s step after a paired look+listen.
    assert _is_next_step_after_listen(2.0, looked, listen, 16.0)
    # Look-only 2s crawl is also skipped.
    assert _is_next_step_after_listen(2.0, looked, None, 16.0)
    # Listen was a different window.
    assert not _is_next_step_after_listen(2.0, looked, (4.0, 6.0), 16.0)
    # They already jumped several seconds.
    assert not _is_next_step_after_listen(8.0, looked, listen, 16.0)


def test_skip_rule_leaves_the_last_six_seconds_alone() -> None:
    looked = [(0.0, 2.0)]
    listen = (0.0, 2.0)
    # remaining == 6 → do not skip (lets a short file finish).
    assert not _is_next_step_after_listen(2.0, looked, listen, 8.0)
    # remaining just over 6 → skip.
    assert _is_next_step_after_listen(2.0, looked, listen, 8.1)
    # Near the end of a 16s file: last look ended at 10s, remaining 6.
    assert not _is_next_step_after_listen(10.0, [(8.0, 10.0)], (8.0, 10.0), 16.0)


def test_look_only_crawl_is_skipped(twelve_s_mp4: Path) -> None:
    brain = FakeBrain(
        [
            _act("look", start_s=0.0, end_s=2.0, fps=1),
            _act("look", start_s=2.0, end_s=4.0, fps=1),
            _act("look", start_s=8.0, end_s=10.0, fps=1),
            _act("answer", answer="Jumped after a blocked look-only crawl."),
        ]
    )
    result = run_loop(twelve_s_mp4, "walk through the whole tape", brain)
    assert any(
        step.do == "look" and step.ok is False and "skip" in (step.detail or "")
        for step in result.steps
    )
    assert any(
        step.do == "look" and step.ok and step.start_s == 8.0 for step in result.steps
    )
    assert result.answer == "Jumped after a blocked look-only crawl."


def test_skip_ahead_blocks_the_next_listen_too(twelve_s_mp4: Path) -> None:
    brain = FakeBrain(
        [
            _act("look", start_s=0.0, end_s=2.0, fps=1),
            _act("listen", start_s=0.0, end_s=2.0),
            _act("listen", start_s=2.0, end_s=4.0),
            _act("look", start_s=7.0, end_s=9.0, fps=1),
            _act("answer", answer="Jumped after a blocked listen."),
        ]
    )
    result = run_loop(twelve_s_mp4, "walk through the whole tape", brain)
    assert any(
        step.do == "listen" and step.ok is False and "skip" in step.detail
        for step in result.steps
    )
    assert any(
        step.do == "look" and step.ok and step.start_s == 7.0 for step in result.steps
    )


def test_mismatched_look_and_listen_does_not_skip(twelve_s_mp4: Path) -> None:
    brain = FakeBrain(
        [
            _act("look", start_s=0.0, end_s=2.0, fps=1),
            _act("listen", start_s=6.0, end_s=8.0),
            _act("look", start_s=2.0, end_s=4.0, fps=1),
            _act("answer", answer="Different windows, crawl allowed."),
        ]
    )
    result = run_loop(twelve_s_mp4, "walk through the whole tape", brain)
    assert all(
        not (step.ok is False and "skip" in (step.detail or ""))
        for step in result.steps
    )
    assert sum(1 for step in result.steps if step.do == "look" and step.ok) == 2


def _tone_hits(_query: str) -> AudioSearchResult:
    return AudioSearchResult(
        hits=[AudioHit(start_s=9.0, end_s=12.0, score=0.9)],
        clusters=[],
        count=0,
    )


def test_search_audio_then_listen_then_export_heard_range(twelve_s_mp4: Path) -> None:
    """OG path: a hit is a range. Listen. Export what you heard. No recut bounce."""
    brain = FakeBrain(
        [
            _act("search_audio", query="tone"),
            _act("listen", start_s=9.0, end_s=12.0),
            _act("export_clip", start_s=10.8, end_s=12.0),
            _act("answer", answer="Clip of the range I heard."),
        ]
    )
    result = run_loop(
        twelve_s_mp4,
        "clip when that sound happens",
        brain,
        search_audio=_tone_hits,
        audio_status=IndexStatus.ready.value,
        export_clip=_export,
    )
    assert result.answer == "Clip of the range I heard."
    assert any(step.do == "listen" and step.ok for step in result.steps)
    exports = [step for step in result.steps if step.do == "export_clip" and step.ok]
    assert [(step.start_s, step.end_s) for step in exports] == [(10.8, 12.0)]
    blob = "\n".join(_user_texts(brain))
    assert "whole search window" not in blob
    assert "not before the middle" not in blob
    assert "Listen at a hit" in blob
    assert "export the range you heard" in blob


def test_exporting_the_full_hit_window_is_not_recut(twelve_s_mp4: Path) -> None:
    """If the model dumps the CLAP range, the laptop cuts that range. No middle recut."""
    brain = FakeBrain(
        [
            _act("search_audio", query="tone"),
            _act("export_clip", start_s=9.0, end_s=12.0),
            _act("answer", answer="Here is the search window."),
        ]
    )
    result = run_loop(
        twelve_s_mp4,
        "clip when that sound happens",
        brain,
        search_audio=_tone_hits,
        audio_status=IndexStatus.ready.value,
        export_clip=_export,
    )
    assert result.answer == "Here is the search window."
    exports = [step for step in result.steps if step.do == "export_clip" and step.ok]
    assert [(step.start_s, step.end_s) for step in exports] == [(9.0, 12.0)]
    blob = "\n".join(_user_texts(brain))
    assert "whole search window" not in blob
    assert "Export again from the middle" not in blob


def test_second_export_after_listen_is_allowed(twelve_s_mp4: Path) -> None:
    brain = FakeBrain(
        [
            _act("search_audio", query="tone"),
            _act("listen", start_s=9.0, end_s=12.0),
            _act("export_clip", start_s=9.0, end_s=12.0),
            _act("export_clip", start_s=10.8, end_s=12.0),
            _act("answer", answer="Tighter clip after a listen."),
        ]
    )
    result = run_loop(
        twelve_s_mp4,
        "clip when that sound happens",
        brain,
        search_audio=_tone_hits,
        audio_status=IndexStatus.ready.value,
        export_clip=_export,
    )
    assert result.answer == "Tighter clip after a listen."
    exports = [step for step in result.steps if step.do == "export_clip" and step.ok]
    assert [(step.start_s, step.end_s) for step in exports] == [
        (9.0, 12.0),
        (10.8, 12.0),
    ]
    assert all(
        not (step.do == "export_clip" and step.ok is False)
        for step in result.steps
    )


def test_audio_observe_does_not_name_an_exam_sound(tiny_mp4: Path) -> None:
    def search(_query: str) -> AudioSearchResult:
        return AudioSearchResult(
            hits=[AudioHit(start_s=0.0, end_s=1.0, score=0.4)],
            clusters=[],
            count=0,
        )

    brain = FakeBrain(
        [
            _act("search_audio", query="knock"),
            _act("answer", answer="I need to listen first."),
        ]
    )
    run_loop(
        tiny_mp4,
        "how many times does that sound happen?",
        brain,
        search_audio=search,
        audio_status=IndexStatus.ready.value,
    )
    observe = brain.calls[1][-1]["content"]
    assert "times to listen" in observe
    assert "Listen at a hit" in observe
    assert "range you heard" in observe
    assert "full search window" not in observe
    assert "cut about 2 seconds" not in observe
    lowered = observe.lower()
    for key in EXAM_KEYS:
        assert key not in lowered


def test_print_vs_speech_answer_is_not_blocked_without_search(tiny_mp4: Path) -> None:
    """E4B needed a bounce. 12B A/B uses this hole; the laptop no longer fills it."""

    def speech(_query: str) -> list[TranscriptHit]:
        return [TranscriptHit(t=0.0, text="they named a number")]

    def slides(_query: str):
        from app.search.slides import SlideHit

        return [
            SlideHit(
                t=0.1,
                t_end=0.4,
                score=0.9,
                slide_id=uuid.uuid4(),
            )
        ]

    brain = FakeBrain(
        [
            _act("search_slides"),
            _act("look", start_s=0.1, end_s=0.3, fps=1),
            _act("answer", answer="Yellow digits; cannot confirm speech."),
        ]
    )
    result = run_loop(
        tiny_mp4,
        "They said a number is also printed on the slide. Does it match what they said?",
        brain,
        search=speech,
        search_slides=slides,
        transcript_status=IndexStatus.ready.value,
        slides_status=IndexStatus.ready.value,
    )
    assert result.answer == "Yellow digits; cannot confirm speech."
    assert all(step.do != "search" for step in result.steps)
    blob = "\n".join(_user_texts(brain))
    assert "not searched what was said" not in blob
    assert "spoken value" not in blob


def test_system_prompt_asks_listen_then_export_not_middle_recut() -> None:
    from app.agent.schema import SYSTEM_PROMPT

    assert "export the range you heard" in SYSTEM_PROMPT
    assert "not before the middle" not in SYSTEM_PROMPT
    assert "whole search window" not in SYSTEM_PROMPT
