"""Laptop skip-ahead / recut rules. Black mp4s, not the exam tape.

These tests are meant to show both what the rule does and where it still
does not fire. They must not mention beep / clap / ship / $99 as answers.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from app.agent.client import FakeBrain
from app.agent.loop import (
    _hit_middle,
    _is_next_step_after_listen,
    run_loop,
)
from app.models import IndexStatus
from app.search.audio import AudioHit, AudioSearchResult
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
    # No listen yet.
    assert not _is_next_step_after_listen(2.0, looked, None, 16.0)
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


def test_hit_middle_only_when_export_is_the_whole_window() -> None:
    windows = [(9.0, 12.0), (1.0, 3.0)]
    assert _hit_middle(9.0, 12.0, windows) == 10.5
    assert _hit_middle(1.0, 3.0, windows) == 2.0
    # Within 0.3s still counts as the same window.
    assert _hit_middle(9.2, 11.9, windows) == 10.5
    # A short cut around the middle is not the whole window.
    assert _hit_middle(10.5, 12.0, windows) is None
    # Overlap that is not the hit bounds.
    assert _hit_middle(8.0, 11.0, windows) is None
    assert _hit_middle(9.0, 12.0, []) is None


def test_look_only_crawl_is_not_skipped(twelve_s_mp4: Path) -> None:
    """Known gap: without a matching listen, 2s looks are allowed."""
    brain = FakeBrain(
        [
            _act("look", start_s=0.0, end_s=2.0, fps=1),
            _act("look", start_s=2.0, end_s=4.0, fps=1),
            _act("answer", answer="Look-only crawl stayed."),
        ]
    )
    result = run_loop(twelve_s_mp4, "walk through the whole tape", brain)
    assert all(
        not (step.ok is False and "skip" in (step.detail or ""))
        for step in result.steps
    )
    assert sum(1 for step in result.steps if step.do == "look" and step.ok) == 2


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


def test_export_that_is_not_a_hit_window_is_not_nudged(twelve_s_mp4: Path) -> None:
    def search(_query: str) -> AudioSearchResult:
        return AudioSearchResult(
            hits=[AudioHit(start_s=9.0, end_s=12.0, score=0.9)],
            clusters=[],
            count=0,
        )

    brain = FakeBrain(
        [
            _act("search_audio", query="tone"),
            _act("export_clip", start_s=0.0, end_s=2.0),
            _act("answer", answer="Unrelated cut is fine."),
        ]
    )
    result = run_loop(
        twelve_s_mp4,
        "clip when that sound happens",
        brain,
        search_audio=search,
        audio_status=IndexStatus.ready.value,
        export_clip=_export,
    )
    assert result.answer == "Unrelated cut is fine."
    texts = [
        call[-1]["content"]
        for call in brain.calls
        if isinstance(call[-1].get("content"), str)
    ]
    assert all("whole search window" not in text for text in texts)


def test_second_full_window_answer_is_still_bounced(twelve_s_mp4: Path) -> None:
    def search(_query: str) -> AudioSearchResult:
        return AudioSearchResult(
            hits=[AudioHit(start_s=9.0, end_s=12.0, score=0.9)],
            clusters=[],
            count=0,
        )

    brain = FakeBrain(
        [
            _act("search_audio", query="tone"),
            _act("export_clip", start_s=9.0, end_s=12.0),
            _act("answer", answer="Here is the full window."),
            _act("answer", answer="Still the full window."),
            _act("export_clip", start_s=10.5, end_s=12.0),
            _act("answer", answer="Shorter clip around the middle."),
        ]
    )
    result = run_loop(
        twelve_s_mp4,
        "clip when that sound happens",
        brain,
        search_audio=search,
        audio_status=IndexStatus.ready.value,
        export_clip=_export,
    )
    assert result.answer == "Shorter clip around the middle."
    assert result.answer != "Still the full window."
    bounces = [
        call[-1]["content"]
        for call in brain.calls
        if isinstance(call[-1].get("content"), str)
        and "whole search window" in call[-1]["content"]
    ]
    # One after the export, plus two refused answers.
    assert len(bounces) >= 3


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
    assert "count is zero" in observe
    assert "full search window" in observe
    lowered = observe.lower()
    for key in EXAM_KEYS:
        assert key not in lowered
