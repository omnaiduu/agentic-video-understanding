"""System One picker: first-hop search routing only. No GPU.

Black mp4s. Do not mention beep / clap / ship / $99 as answers.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.agent.client import FakeBrain
from app.agent.loop import run_loop
from app.agent.picker import (
    DEFAULT_MIN_P,
    LogitPicker,
    FakePicker,
    PickerDecision,
    SEARCH_DOS,
    build_picker,
    decide_picker,
    last_user_is_text,
    letter_logits,
    normalize_letter_token,
    picker_allowed,
    routing_options,
    softmax,
)
from app.main import app
from app.models import IndexStatus
from app.routes.chat import get_brain, get_picker
from app.search.audio import AudioHit, AudioSearchResult
from app.search.transcript import TranscriptHit
from app.settings import Settings


EXAM_KEYS = (
    "beep",
    "ship the slide",
    "$99",
    "red alert",
    "q3 roadmap",
    "11.0s",
)


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


def _ready_options():
    return routing_options(
        transcript_status=IndexStatus.ready.value,
        visual_status=IndexStatus.ready.value,
        audio_status=IndexStatus.ready.value,
        slides_status=IndexStatus.ready.value,
    )


def test_softmax_is_a_probability_distribution() -> None:
    probs = softmax([-0.1, -2.0, -3.0])
    assert len(probs) == 3
    assert abs(sum(probs) - 1.0) < 1e-9
    assert probs[0] == max(probs)
    assert probs[0] > 0.7
    assert softmax([]) == []
    even = softmax([1.0, 1.0, 1.0, 1.0])
    assert all(abs(p - 0.25) < 1e-9 for p in even)


def test_letter_tokens_from_sentencepiece_and_spaces() -> None:
    assert normalize_letter_token("A") == "A"
    assert normalize_letter_token("▁A") == "A"
    assert normalize_letter_token(" A") == "A"
    assert normalize_letter_token("A\n") == "A"
    assert normalize_letter_token("b") == "B"
    assert normalize_letter_token("A.") == "A"
    assert normalize_letter_token("") == ""
    logits = letter_logits(
        [("▁B", -0.2), ("A", -1.5), ("B", -0.4), ("C", -3.0)],
        ["A", "B", "C", "D"],
    )
    assert logits["B"] == -0.2
    assert logits["A"] == -1.5
    assert logits["D"] == -100.0


def test_routing_options_only_ready_books_plus_abstain() -> None:
    options = routing_options(
        transcript_status=IndexStatus.ready.value,
        visual_status=IndexStatus.pending.value,
        audio_status=IndexStatus.ready.value,
        slides_status=IndexStatus.skipped.value,
    )
    assert [option.do for option in options] == ["search", "search_audio", None]
    assert [option.letter for option in options] == ["A", "B", "C"]
    full = _ready_options()
    assert [option.do for option in full] == [
        "search",
        "search_visual",
        "search_audio",
        "search_slides",
        None,
    ]


def test_decide_picker_commit_fallback_and_shadow() -> None:
    commit = decide_picker(
        PickerDecision(letter="A", do="search", p_max=0.81, probs={"search": 0.81}),
        min_p=DEFAULT_MIN_P,
    )
    assert commit.used is True
    assert commit.reason == "commit"

    low = decide_picker(
        PickerDecision(letter="A", do="search", p_max=0.4, probs={"search": 0.4}),
        min_p=DEFAULT_MIN_P,
    )
    assert low.used is False
    assert low.reason == "low_confidence"

    abstain = decide_picker(
        PickerDecision(letter="E", do=None, p_max=0.9, probs={"abstain": 0.9}),
    )
    assert abstain.used is False
    assert abstain.reason == "abstain"

    look = decide_picker(
        PickerDecision(letter="A", do="look", p_max=0.99, probs={"look": 0.99}),
    )
    assert look.used is False
    assert look.reason == "not_search"

    shadow = decide_picker(
        PickerDecision(letter="A", do="search", p_max=0.9, probs={"search": 0.9}),
        shadow=True,
    )
    assert shadow.used is False
    assert shadow.reason == "shadow"

    unknown = decide_picker(
        PickerDecision(letter="", do="search", p_max=0.9),
    )
    assert unknown.used is False
    assert unknown.reason == "unknown_option"


def test_picker_allowed_is_first_text_hop_only() -> None:
    picker = FakePicker(["search"])
    text_messages = [{"role": "user", "content": "Question: how much?"}]
    kwargs = dict(
        picker=picker,
        steps=[],
        last_times=None,
        force_answer=False,
        messages=text_messages,
        thinking_brain=False,
        already_tried=False,
    )
    assert picker_allowed(**kwargs)
    assert not picker_allowed(**{**kwargs, "picker": None})
    assert not picker_allowed(**{**kwargs, "already_tried": True})
    assert not picker_allowed(**{**kwargs, "force_answer": True})
    assert not picker_allowed(**{**kwargs, "thinking_brain": True})
    assert not picker_allowed(**{**kwargs, "steps": [object()]})
    assert not picker_allowed(**{**kwargs, "last_times": [{"start_s": 1.0}]})
    media = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "frames"},
                {"type": "image_url", "image_url": {"url": "x"}},
            ],
        }
    ]
    assert not picker_allowed(**{**kwargs, "messages": media})
    assert last_user_is_text(text_messages)
    assert not last_user_is_text(media)


def test_build_picker_modes() -> None:
    off = Settings(
        database_url="postgresql+psycopg://video:video@127.0.0.1:5432/video_test",
        picker="off",
    )
    assert build_picker(off) is None
    fake = Settings(
        database_url="postgresql+psycopg://video:video@127.0.0.1:5432/video_test",
        picker="fake",
    )
    assert build_picker(fake) is None
    try:
        build_picker(
            Settings(
                database_url="postgresql+psycopg://video:video@127.0.0.1:5432/video_test",
                picker="nope",
            )
        )
        raise AssertionError("expected unknown PICKER")
    except RuntimeError as exc:
        assert "unknown PICKER" in str(exc)
    try:
        LogitPicker(
            Settings(
                database_url="postgresql+psycopg://video:video@127.0.0.1:5432/video_test",
                picker="logit",
                vllm_base_url="",
            )
        )
        raise AssertionError("expected missing URL")
    except RuntimeError as exc:
        assert "VLLM_BASE_URL" in str(exc)


def test_logit_picker_softmaxes_letter_logprobs(monkeypatch) -> None:
    captured: dict = {}

    class Item:
        def __init__(self, token: str, logprob: float) -> None:
            self.token = token
            self.logprob = logprob

    class FakeResponse:
        choices = [
            SimpleNamespace(
                logprobs=SimpleNamespace(
                    content=[
                        SimpleNamespace(
                            token="A",
                            logprob=-0.1,
                            top_logprobs=[
                                Item("A", -0.1),
                                Item("B", -2.0),
                                Item("C", -3.0),
                                Item("D", -4.0),
                                Item("E", -5.0),
                            ],
                        )
                    ]
                )
            )
        ]

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return FakeResponse()

    class FakeOpenAI:
        def __init__(self, **kwargs) -> None:
            captured["base_url"] = kwargs.get("base_url")
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr("openai.OpenAI", FakeOpenAI)
    picker = LogitPicker(
        Settings(
            database_url="postgresql+psycopg://video:video@127.0.0.1:5432/video_test",
            vllm_base_url="http://vllm.example/v1",
            vllm_model="google/gemma-4-E4B-it",
        )
    )
    score = picker.score("How much does it cost?", _ready_options(), context="dur 1s")
    assert captured["max_tokens"] == 1
    assert captured["logprobs"] is True
    assert captured["top_logprobs"] == 20
    assert captured.get("response_format") is None
    assert "tools" not in captured
    assert score.do == "search"
    assert score.letter == "A"
    assert score.p_max > 0.7
    assert abs(sum(score.probs.values()) - 1.0) < 1e-6


def test_picker_source_does_not_name_exam_answers() -> None:
    root = Path(__file__).resolve().parents[1] / "app" / "agent"
    blob = (root / "picker.py").read_text().lower()
    for key in EXAM_KEYS:
        assert key not in blob, f"exam answer {key!r} leaked into picker"


def test_fake_picker_opens_spoken_words_without_json(
    tiny_mp4: Path,
) -> None:
    hits = [TranscriptHit(t=0.2, text="the monthly plan")]
    brain = FakeBrain(
        [_act("answer", answer="Opened spoken words.", times=[0.2])]
    )
    picker = FakePicker(["search"])
    result = run_loop(
        tiny_mp4,
        "How much does the plan cost?",
        brain,
        picker=picker,
        search=lambda query: hits if query else [],
        transcript_status=IndexStatus.ready.value,
        visual_status=IndexStatus.ready.value,
        audio_status=IndexStatus.ready.value,
        slides_status=IndexStatus.ready.value,
    )
    assert result.picker is not None
    assert result.picker.used is True
    assert result.picker.do == "search"
    assert result.picker.reason == "commit"
    assert [step.do for step in result.steps] == ["search", "answer"]
    assert result.steps[0].ok is True
    assert result.steps[0].detail.startswith("How much does the plan cost?")
    assert len(brain.calls) == 1
    assert result.answer == "Opened spoken words."
    assert picker.calls[0][0] == "How much does the plan cost?"


def test_low_confidence_falls_back_to_json_brain(tiny_mp4: Path) -> None:
    brain = FakeBrain(
        [
            _act("look", start_s=0.1, end_s=0.3, fps=1),
            _act("answer", answer="Looked because the picker was unsure."),
        ]
    )
    picker = FakePicker(["search"], p_max=0.4)
    result = run_loop(
        tiny_mp4,
        "what is on screen?",
        brain,
        picker=picker,
        search=lambda _q: [TranscriptHit(t=0.2, text="hi")],
        transcript_status=IndexStatus.ready.value,
        visual_status=IndexStatus.ready.value,
        audio_status=IndexStatus.ready.value,
        slides_status=IndexStatus.ready.value,
    )
    assert result.picker is not None
    assert result.picker.used is False
    assert result.picker.reason == "low_confidence"
    assert result.steps[0].do == "look"
    assert len(brain.calls) == 2


def test_abstain_and_look_never_replace_the_json_form(tiny_mp4: Path) -> None:
    brain = FakeBrain(
        [
            _act("look", start_s=0.1, end_s=0.3, fps=1),
            _act("answer", answer="Timed look is Gemma's job.", times=[0.1]),
        ]
    )
    picker = FakePicker(["abstain"], p_max=0.95)
    result = run_loop(
        tiny_mp4,
        "what happens at 0:10?",
        brain,
        picker=picker,
        transcript_status=IndexStatus.ready.value,
        visual_status=IndexStatus.ready.value,
        audio_status=IndexStatus.ready.value,
        slides_status=IndexStatus.ready.value,
    )
    assert result.picker is not None
    assert result.picker.used is False
    assert result.picker.reason == "abstain"
    assert result.steps[0].do == "look"
    assert len(brain.calls) >= 1

    brain2 = FakeBrain(
        [_act("look", start_s=0.1, end_s=0.3, fps=1), _act("answer", answer="ok")]
    )
    result2 = run_loop(
        tiny_mp4,
        "what is on screen?",
        brain2,
        picker=FakePicker(["look"], p_max=0.99),
        transcript_status=IndexStatus.ready.value,
        visual_status=IndexStatus.ready.value,
        audio_status=IndexStatus.ready.value,
        slides_status=IndexStatus.ready.value,
    )
    assert result2.picker is not None
    assert result2.picker.used is False
    assert result2.picker.reason == "not_search"
    assert result2.steps[0].do == "look"


def test_shadow_scores_but_still_asks_json(tiny_mp4: Path) -> None:
    brain = FakeBrain(
        [
            _act("search_visual"),
            _act("answer", answer="JSON still chose pictures."),
        ]
    )
    picker = FakePicker(["search"], p_max=0.88, shadow=True)
    result = run_loop(
        tiny_mp4,
        "is there a colored screen?",
        brain,
        picker=picker,
        search_visual=lambda _q: [],
        transcript_status=IndexStatus.ready.value,
        visual_status=IndexStatus.ready.value,
        audio_status=IndexStatus.ready.value,
        slides_status=IndexStatus.ready.value,
    )
    assert result.picker is not None
    assert result.picker.used is False
    assert result.picker.reason == "shadow"
    assert result.picker.do == "search"
    assert result.steps[0].do == "search_visual"
    assert len(brain.calls) >= 1


def test_picker_is_not_used_on_follow_up_or_second_hop(tiny_mp4: Path) -> None:
    brain = FakeBrain(
        [
            _act("look", start_s=0.1, end_s=0.3, fps=1),
            _act("answer", answer="Follow-up used last times."),
        ]
    )
    picker = FakePicker(["search"])
    result = run_loop(
        tiny_mp4,
        "what about that frame?",
        brain,
        picker=picker,
        last_times=[{"start_s": 0.1, "end_s": 0.3}],
        transcript_status=IndexStatus.ready.value,
        visual_status=IndexStatus.ready.value,
        audio_status=IndexStatus.ready.value,
        slides_status=IndexStatus.ready.value,
    )
    assert result.picker is None
    assert picker.calls == []
    assert result.steps[0].do == "look"

    brain2 = FakeBrain(
        [
            _act("look", start_s=0.1, end_s=0.3, fps=1),
            _act("answer", answer="Second hop is JSON."),
        ]
    )
    picker2 = FakePicker(["search"])
    result2 = run_loop(
        tiny_mp4,
        "How much does the plan cost?",
        brain2,
        picker=picker2,
        search=lambda _q: [TranscriptHit(t=0.1, text="plan")],
        transcript_status=IndexStatus.ready.value,
        visual_status=IndexStatus.ready.value,
        audio_status=IndexStatus.ready.value,
        slides_status=IndexStatus.ready.value,
    )
    assert result2.picker is not None
    assert result2.picker.used is True
    assert len(picker2.calls) == 1
    assert [step.do for step in result2.steps] == ["search", "look", "answer"]


def test_picker_search_audio_then_json_listen(tiny_mp4: Path) -> None:
    def search_audio(_query: str) -> AudioSearchResult:
        return AudioSearchResult(
            hits=[AudioHit(start_s=0.0, end_s=0.5, score=0.8)],
            clusters=[],
            count=0,
        )

    brain = FakeBrain(
        [
            _act("listen", start_s=0.0, end_s=0.5),
            _act("answer", answer="Heard the tone."),
        ]
    )
    result = run_loop(
        tiny_mp4,
        "when does that tone play?",
        brain,
        picker=FakePicker(["search_audio"]),
        search_audio=search_audio,
        transcript_status=IndexStatus.ready.value,
        visual_status=IndexStatus.ready.value,
        audio_status=IndexStatus.ready.value,
        slides_status=IndexStatus.ready.value,
    )
    assert result.picker is not None
    assert result.picker.do == "search_audio"
    assert result.picker.used is True
    assert result.steps[0].do == "search_audio"
    assert result.steps[1].do == "listen"
    assert result.answer == "Heard the tone."


def test_thinking_brain_skips_picker(tiny_mp4: Path) -> None:
    brain = FakeBrain(
        [
            _act("look", start_s=0.1, end_s=0.3, fps=1),
            _act("answer", answer="Thinking path keeps JSON."),
        ]
    )
    brain.thinking = True
    picker = FakePicker(["search"])
    result = run_loop(
        tiny_mp4,
        "How much does the plan cost?",
        brain,
        picker=picker,
        search=lambda _q: [TranscriptHit(t=0.1, text="plan")],
        transcript_status=IndexStatus.ready.value,
        visual_status=IndexStatus.ready.value,
        audio_status=IndexStatus.ready.value,
        slides_status=IndexStatus.ready.value,
    )
    assert result.picker is None
    assert picker.calls == []
    assert result.steps[0].do == "look"


def test_picker_gpu_error_falls_back(tiny_mp4: Path) -> None:
    class BoomPicker:
        shadow = False

        def score(self, question, options, *, context=""):
            raise RuntimeError("picker GPU unavailable")

    brain = FakeBrain(
        [
            _act("look", start_s=0.1, end_s=0.3, fps=1),
            _act("answer", answer="JSON after picker error.", times=[0.0]),
        ]
    )
    result = run_loop(
        tiny_mp4,
        "what is this?",
        brain,
        picker=BoomPicker(),
        transcript_status=IndexStatus.ready.value,
        visual_status=IndexStatus.ready.value,
        audio_status=IndexStatus.ready.value,
        slides_status=IndexStatus.ready.value,
    )
    assert result.picker is not None
    assert result.picker.used is False
    assert result.picker.reason == "error"
    assert result.answer == "JSON after picker error."


def _upload(client, path: Path):
    with path.open("rb") as handle:
        return client.post(
            "/videos",
            files={"file": (path.name, handle, "application/octet-stream")},
        )


def _override(brain: FakeBrain, picker: FakePicker | None = None) -> None:
    app.dependency_overrides[get_brain] = lambda: brain
    if picker is not None:
        app.dependency_overrides[get_picker] = lambda: picker


def _clear_override() -> None:
    app.dependency_overrides.pop(get_brain, None)
    app.dependency_overrides.pop(get_picker, None)


def test_chat_default_has_no_picker(client, tiny_mp4: Path) -> None:
    video_id = _upload(client, tiny_mp4).json()["id"]
    brain = FakeBrain(
        [
            _act("look", start_s=0.1, end_s=0.4, fps=1),
            _act("answer", answer="A dark frame.", times=[0.1]),
        ]
    )
    _override(brain)
    try:
        body = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "what happens at 0:10?"},
        ).json()
    finally:
        _clear_override()
    assert body["picker"] is None
    assert [step["do"] for step in body["steps"]] == ["look", "answer"]


def test_chat_fake_picker_first_hop(client, tiny_mp4: Path) -> None:
    video_id = _upload(client, tiny_mp4).json()["id"]
    brain = FakeBrain(
        [_act("answer", answer="Opened spoken words.", times=[0.0])]
    )
    picker = FakePicker(["search"])
    _override(brain, picker)
    try:
        response = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "How much does the plan cost?"},
        )
    finally:
        _clear_override()
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["picker"]["used"] is True
    assert body["picker"]["do"] == "search"
    assert body["picker"]["reason"] == "commit"
    assert body["steps"][0]["do"] == "search"
    assert body["answer"] == "Opened spoken words."
    assert len(brain.calls) == 1


def test_chat_thinking_skips_injected_picker(client, tiny_mp4: Path) -> None:
    video_id = _upload(client, tiny_mp4).json()["id"]
    brain = FakeBrain(
        [
            _act("look", start_s=0.1, end_s=0.4, fps=1),
            _act("answer", answer="Thinking keeps JSON.", times=[0.1]),
        ]
    )
    picker = FakePicker(["search"])
    _override(brain, picker)
    try:
        body = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "How much does the plan cost?", "thinking": True},
        ).json()
    finally:
        _clear_override()
    assert body["thinking"] is True
    assert body["picker"] is None
    assert picker.calls == []
    assert body["steps"][0]["do"] == "look"


def test_picker_logit_without_url_503(
    client, tiny_mp4: Path, monkeypatch
) -> None:
    from app.settings import get_settings

    monkeypatch.setenv("PICKER", "logit")
    monkeypatch.setenv("VLLM_BASE_URL", "")
    get_settings.cache_clear()
    video_id = _upload(client, tiny_mp4).json()["id"]
    brain = FakeBrain(
        [_act("answer", answer="should not run", times=[])]
    )
    _override(brain)
    try:
        response = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "what happens at 0:10?"},
        )
        assert response.status_code == 503
        assert "VLLM_BASE_URL" in response.json()["detail"]
    finally:
        monkeypatch.setenv("PICKER", "off")
        get_settings.cache_clear()
        _clear_override()


def test_default_picker_setting_is_off() -> None:
    assert Settings.model_fields["picker"].default == "off"
    assert Settings.model_fields["picker_min_p"].default == 0.55
    assert "look" not in SEARCH_DOS
    assert "listen" not in SEARCH_DOS
    assert "answer" not in SEARCH_DOS
    assert "export_clip" not in SEARCH_DOS
