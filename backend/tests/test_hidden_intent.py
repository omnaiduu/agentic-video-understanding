"""Catalog for the E4B vs 12B hidden-intent A/B. Does not call a GPU."""

from __future__ import annotations

from eval.hidden_intent import E4B_OBSERVATIONS, QUESTIONS, question_ids
from eval.run_hidden_intent_suite import listened_before_export, searched_speech


def test_suite_has_the_eight_e4b_questions() -> None:
    ids = question_ids()
    assert ids == ["E1", "H1", "M3", "M4", "M1", "H5", "H7", "H8"]
    by_id = dict(QUESTIONS)
    assert "How much does Pro cost?" in by_id["E1"]
    assert "beep" in by_id["H7"]
    assert "claps" in by_id["H5"]
    assert "Walk through the whole tape" in by_id["H8"]
    assert "printed on the slide" in by_id["M1"]


def test_e4b_notes_cover_every_question_and_name_the_crutches() -> None:
    assert set(E4B_OBSERVATIONS) == set(question_ids())
    h7 = E4B_OBSERVATIONS["H7"]
    assert "RANGE" in h7["what_happened"] or "range" in h7["what_happened"]
    assert "recut" in h7["fragile_crutch_we_removed"]
    assert "listen" in h7["what_12b_should_try_without_a_bounce"]
    m1 = E4B_OBSERVATIONS["M1"]
    assert "bounce" in m1["fragile_crutch_we_removed"]
    h8 = E4B_OBSERVATIONS["H8"]
    assert "none" in h8["fragile_crutch_we_removed"]


def test_suite_flags_listen_before_export_and_speech() -> None:
    steps = [
        {"do": "search_audio", "ok": True},
        {"do": "listen", "ok": True},
        {"do": "export_clip", "ok": True},
        {"do": "answer", "ok": True},
    ]
    assert listened_before_export(steps) is True
    assert searched_speech(steps) is False
    dump = [
        {"do": "search_audio", "ok": True},
        {"do": "export_clip", "ok": True},
        {"do": "answer", "ok": True},
    ]
    assert listened_before_export(dump) is False
    assert searched_speech(
        [{"do": "search", "ok": True}, {"do": "answer", "ok": True}]
    )
