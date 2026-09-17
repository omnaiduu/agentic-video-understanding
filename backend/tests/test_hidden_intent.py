"""A/B catalog, scorer, and 12B worker file. Does not call a GPU."""

from __future__ import annotations

from pathlib import Path

from app.settings import Settings
from eval.brains import (
    E4B_HF_ID,
    E4B_MODAL_APP,
    E4B_THINKING_MODAL_APP,
    EXAM_TAPE_ID,
    TWELVE_B_HF_ID,
    TWELVE_B_MODAL_APP,
    TWELVE_B_WEIGHTS,
)
from eval.hidden_intent import E4B_OBSERVATIONS, QUESTIONS, question_ids
from eval.score_hidden_intent import (
    dumped_unheard_clap_window,
    exported_heard_range,
    listened_before_export,
    score_question,
    score_run,
    searched_speech,
)

BACKEND = Path(__file__).resolve().parents[1]


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


def test_export_of_heard_range_is_not_an_unheard_clap_dump() -> None:
    heard = [
        {"do": "search_audio", "ok": True, "start_s": 9.0, "end_s": 12.0},
        {"do": "listen", "ok": True, "start_s": 10.5, "end_s": 12.5},
        {"do": "export_clip", "ok": True, "start_s": 10.5, "end_s": 12.5},
    ]
    assert exported_heard_range(heard) is True
    assert dumped_unheard_clap_window(heard) is False
    dump = [
        {"do": "search_audio", "ok": True, "start_s": 9.0, "end_s": 12.0},
        {"do": "export_clip", "ok": True, "start_s": 9.0, "end_s": 12.0},
    ]
    assert listened_before_export(dump) is False
    assert dumped_unheard_clap_window(dump) is True
    listen_then_same_window = [
        {"do": "search_audio", "ok": True, "start_s": 9.0, "end_s": 12.0},
        {"do": "listen", "ok": True, "start_s": 9.0, "end_s": 12.0},
        {"do": "export_clip", "ok": True, "start_s": 9.0, "end_s": 12.0},
    ]
    assert exported_heard_range(listen_then_same_window) is True
    assert dumped_unheard_clap_window(listen_then_same_window) is False


def test_h7_pass_requires_listen_then_heard_export() -> None:
    pass_body = {
        "http": 200,
        "answer": "clip of the beep",
        "steps": [
            {"do": "search_audio", "ok": True, "start_s": 9.0, "end_s": 12.0},
            {"do": "listen", "ok": True, "start_s": 10.8, "end_s": 12.0},
            {"do": "export_clip", "ok": True, "start_s": 10.8, "end_s": 12.0},
            {"do": "answer", "ok": True},
        ],
    }
    assert score_question("H7", pass_body)["verdict"] == "pass"
    dump = {
        "http": 200,
        "answer": "here is the clip",
        "steps": [
            {"do": "search_audio", "ok": True, "start_s": 9.0, "end_s": 12.0},
            {"do": "export_clip", "ok": True, "start_s": 9.0, "end_s": 12.0},
            {"do": "answer", "ok": True},
        ],
    }
    assert score_question("H7", dump)["verdict"] == "fail"


def test_m1_fails_without_speech_search() -> None:
    body = {
        "http": 200,
        "answer": "The number is yellow. Cannot confirm it matches.",
        "steps": [
            {"do": "look", "ok": True, "start_s": 0.0, "end_s": 2.0},
            {"do": "answer", "ok": True},
        ],
    }
    assert score_question("M1", body)["verdict"] == "fail"
    both = {
        "http": 200,
        "answer": "Yellow $99 matches the spoken $99.",
        "steps": [
            {"do": "look", "ok": True, "start_s": 0.0, "end_s": 2.0},
            {"do": "search", "ok": True, "start_s": 0.0, "end_s": 0.0},
            {"do": "answer", "ok": True},
        ],
    }
    assert score_question("M1", both)["verdict"] == "pass"


def test_h5_zero_after_listen_passes_invented_count_fails() -> None:
    zero = {
        "http": 200,
        "answer": "There are zero claps in this recording.",
        "steps": [
            {"do": "search_audio", "ok": True, "start_s": 7.5, "end_s": 9.0},
            {"do": "listen", "ok": True, "start_s": 7.5, "end_s": 9.0},
            {"do": "answer", "ok": True},
        ],
    }
    assert score_question("H5", zero)["verdict"] == "pass"
    invented = {
        "http": 200,
        "answer": "I heard one clap.",
        "steps": [
            {"do": "search_audio", "ok": True, "start_s": 7.5, "end_s": 9.0},
            {"do": "listen", "ok": True, "start_s": 7.5, "end_s": 9.0},
            {"do": "answer", "ok": True},
        ],
    }
    assert score_question("H5", invented)["verdict"] == "fail"


def test_h1_yes_trap_fails() -> None:
    trap = {
        "http": 200,
        "answer": "Yes, the $99 price is on the red emergency screen.",
        "steps": [{"do": "look", "ok": True, "start_s": 6.0, "end_s": 8.0}],
    }
    assert score_question("H1", trap)["verdict"] == "fail"
    reject = {
        "http": 200,
        "answer": "No. The $99 is on the navy Pricing slide, not on red.",
        "steps": [{"do": "look", "ok": True, "start_s": 0.0, "end_s": 2.0}],
    }
    assert score_question("H1", reject)["verdict"] == "pass"


def test_score_run_covers_every_catalog_question() -> None:
    payload = {
        "brain_label": "12b",
        "video_id": EXAM_TAPE_ID,
        "questions": {
            "E1": {"http": 200, "answer": "$99 a month", "steps": []},
        },
    }
    scored = score_run(payload)
    assert scored["order"] == question_ids()
    assert scored["questions"]["E1"]["verdict"] == "pass"
    assert scored["questions"]["H7"]["verdict"] == "fail"


def test_default_vllm_model_stays_e4b() -> None:
    assert Settings.model_fields["vllm_model"].default == E4B_HF_ID
    assert Settings.model_fields["gemma_thinking"].default is False
    assert Settings.model_fields["vllm_thinking_base_url"].default == ""
    assert E4B_HF_ID == "google/gemma-4-E4B-it"
    assert TWELVE_B_HF_ID == "google/gemma-4-12B-it"
    assert TWELVE_B_WEIGHTS.endswith("qat-w4a16-ct")
    assert TWELVE_B_MODAL_APP != E4B_MODAL_APP
    assert E4B_THINKING_MODAL_APP != E4B_MODAL_APP
    assert E4B_THINKING_MODAL_APP != TWELVE_B_MODAL_APP


def test_e4b_modal_file_is_unchanged_app() -> None:
    src = (BACKEND / "modal_brain.py").read_text()
    assert 'MODEL_NAME = "google/gemma-4-E4B-it"' in src
    assert 'app = modal.App("agentic-video-brain")' in src
    assert "agentic-video-brain-12b" not in src
    assert "agentic-video-brain-e4b-thinking" not in src
    assert "gemma-4-12B-it" not in src
    assert "--reasoning-parser" not in src
    assert "--enable-auto-tool-choice" not in src


def test_e4b_thinking_modal_file_adds_parser_only() -> None:
    src = (BACKEND / "modal_brain_thinking.py").read_text()
    assert 'MODEL_NAME = "google/gemma-4-E4B-it"' in src
    assert f'app = modal.App("{E4B_THINKING_MODAL_APP}")' in src
    assert "--reasoning-parser" in src
    assert "gemma4" in src
    assert "--enable-auto-tool-choice" not in src
    assert "--tool-call-parser" not in src
    assert "agentic-video-brain-12b" not in src
    assert 'app = modal.App("agentic-video-brain")' not in src
    e4b = (BACKEND / "modal_brain.py").read_text()
    assert "--reasoning-parser" not in e4b


def test_12b_modal_file_is_a_second_app_on_qat_weights() -> None:
    src = (BACKEND / "modal_brain_12b.py").read_text()
    assert 'MODEL_NAME = "google/gemma-4-12B-it"' in src
    assert 'WEIGHTS = "google/gemma-4-12B-it-qat-w4a16-ct"' in src
    assert 'app = modal.App("agentic-video-brain-12b")' in src
    assert "google/gemma-4-E4B-it" not in src
    assert 'app = modal.App("agentic-video-brain")' not in src
    assert "--max-model-len" in src
    assert "8192" in src
    assert '"image": 64' in src
    assert '"audio": 1' in src
    assert 'gpu="L4"' in src
    assert "--served-model-name" in src
    assert "WEIGHTS" in src
    assert "--enable-auto-tool-choice" not in src
    assert "--reasoning-parser" not in src
    assert "patch_gemma4_unified_audio_dummy.py" in src
    patch = (BACKEND / "modal_patches/patch_gemma4_unified_audio_dummy.py").read_text()
    assert "fft_length" in patch
    assert "audio_samples_per_token" in patch
    e4b = (BACKEND / "modal_brain.py").read_text()
    assert "patch_gemma4_unified_audio_dummy" not in e4b
