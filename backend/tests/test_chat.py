from __future__ import annotations

from pathlib import Path

from app.agent.client import FakeBrain, VllmBrain
from app.agent.loop import LoopError, run_loop
from app.agent.schema import RESPONSE_FORMAT, parse_action
from app.main import app
from app.models import ChatMessage, ChatSession, Video
from app.routes.chat import get_brain
from sqlmodel import Session, select


def _upload(client, path: Path):
    with path.open("rb") as handle:
        return client.post(
            "/videos",
            files={"file": (path.name, handle, "application/octet-stream")},
        )


def _look_then_answer() -> FakeBrain:
    return FakeBrain(
        [
            {
                "do": "look",
                "start_s": 0.1,
                "end_s": 0.5,
                "fps": 2,
                "answer": None,
                "times": [],
            },
            {
                "do": "answer",
                "start_s": None,
                "end_s": None,
                "fps": None,
                "answer": "A dark frame at 0.1s.",
                "times": [0.1],
            },
        ]
    )


def _override(brain: FakeBrain) -> None:
    app.dependency_overrides[get_brain] = lambda: brain


def _clear_override() -> None:
    app.dependency_overrides.pop(get_brain, None)


def test_chat_look_then_answer_attaches_images(client, tiny_mp4: Path) -> None:
    video_id = _upload(client, tiny_mp4).json()["id"]
    brain = _look_then_answer()
    _override(brain)
    try:
        response = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "what happens at 0:10?"},
        )
    finally:
        _clear_override()
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["answer"] == "A dark frame at 0.1s."
    assert body["citations"] == [0.1]
    assert body["session_id"]
    assert [step["do"] for step in body["steps"]] == ["look", "answer"]
    assert body["steps"][0]["ok"] is True
    assert len(brain.calls) == 2
    observation = brain.calls[1][-1]
    assert observation["role"] == "user"
    parts = observation["content"]
    assert isinstance(parts, list)
    assert any(part.get("type") == "image_url" for part in parts)
    assert all(part.get("type") != "tool" for part in parts)


def test_oversize_look_never_extracts(client, tiny_mp4: Path, monkeypatch) -> None:
    from app.tools import ffmpeg_cli

    def boom(*_args, **_kwargs) -> None:
        raise AssertionError("extract ffmpeg must not run for an oversize look")

    monkeypatch.setattr(ffmpeg_cli, "run_ffmpeg", boom)
    video_id = _upload(client, tiny_mp4).json()["id"]
    brain = FakeBrain(
        [
            {
                "do": "look",
                "start_s": 0,
                "end_s": 7200,
                "fps": 1,
                "answer": None,
                "times": [],
            },
            {
                "do": "answer",
                "start_s": None,
                "end_s": None,
                "fps": None,
                "answer": "Need a smaller window.",
                "times": [],
            },
        ]
    )
    _override(brain)
    try:
        response = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "what happens at 0:10?"},
        )
    finally:
        _clear_override()
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["steps"][0]["do"] == "look"
    assert body["steps"][0]["ok"] is False
    assert "64" in body["steps"][0]["detail"]
    refuse = brain.calls[1][-1]["content"]
    assert "refused" in refuse
    assert body["answer"] == "Need a smaller window."


def test_listen_attaches_audio_part(client, tiny_mp4: Path) -> None:
    video_id = _upload(client, tiny_mp4).json()["id"]
    brain = FakeBrain(
        [
            {
                "do": "listen",
                "start_s": 0.0,
                "end_s": 0.5,
                "fps": None,
                "answer": None,
                "times": [],
            },
            {
                "do": "answer",
                "start_s": None,
                "end_s": None,
                "fps": None,
                "answer": "A tone.",
                "times": [0.0],
            },
        ]
    )
    _override(brain)
    try:
        response = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "what do I hear at the start?"},
        )
    finally:
        _clear_override()
    assert response.status_code == 200, response.text
    parts = brain.calls[1][-1]["content"]
    assert any(part.get("type") == "input_audio" for part in parts)


def test_second_listen_keeps_only_one_audio_part(client, tiny_mp4: Path) -> None:
    video_id = _upload(client, tiny_mp4).json()["id"]
    brain = FakeBrain(
        [
            {
                "do": "listen",
                "start_s": 0.0,
                "end_s": 0.4,
                "fps": None,
                "query": None,
                "answer": None,
                "times": [],
            },
            {
                "do": "listen",
                "start_s": 0.1,
                "end_s": 0.5,
                "fps": None,
                "query": None,
                "answer": None,
                "times": [],
            },
            {
                "do": "answer",
                "start_s": None,
                "end_s": None,
                "fps": None,
                "query": None,
                "answer": "Two listens.",
                "times": [0.1],
            },
        ]
    )
    _override(brain)
    try:
        response = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "listen twice then answer"},
        )
    finally:
        _clear_override()
    assert response.status_code == 200, response.text
    third = brain.calls[2]
    audios = 0
    for msg in third:
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        audios += sum(
            1
            for part in content
            if isinstance(part, dict) and part.get("type") == "input_audio"
        )
    assert audios == 1


def test_chat_stores_text_not_jpegs(client, tiny_mp4: Path) -> None:
    from app.db import get_engine

    video_id = _upload(client, tiny_mp4).json()["id"]
    _override(_look_then_answer())
    try:
        body = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "what happens at 0:10?"},
        ).json()
    finally:
        _clear_override()
    engine = get_engine()
    with Session(engine) as session:
        rows = session.exec(select(ChatMessage)).all()
        assert rows
        joined = " ".join(row.content for row in rows)
        assert "\xff\xd8" not in joined
        assert "data:image" not in joined
        chat = session.get(ChatSession, body["session_id"])
        assert chat is not None
        assert str(chat.video_id) == video_id


def test_delete_video_removes_sessions(client, tiny_mp4: Path) -> None:
    from app.db import get_engine

    video_id = _upload(client, tiny_mp4).json()["id"]
    _override(_look_then_answer())
    try:
        session_id = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "what happens at 0:10?"},
        ).json()["session_id"]
    finally:
        _clear_override()
    assert client.delete(f"/videos/{video_id}").status_code == 204
    engine = get_engine()
    with Session(engine) as session:
        assert session.get(ChatSession, session_id) is None
        assert session.exec(select(ChatMessage)).all() == []
        assert session.get(Video, video_id) is None


def test_wrong_session_404(client, tiny_mp4: Path) -> None:
    video_id = _upload(client, tiny_mp4).json()["id"]
    missing = "00000000-0000-0000-0000-000000000099"
    response = client.post(
        f"/videos/{video_id}/chat",
        json={"message": "hello", "session_id": missing},
    )
    assert response.status_code == 404


def test_chat_without_injected_brain_503(client, tiny_mp4: Path) -> None:
    video_id = _upload(client, tiny_mp4).json()["id"]
    response = client.post(
        f"/videos/{video_id}/chat",
        json={"message": "what happens at 0:10?"},
    )
    assert response.status_code == 503


def test_chat_missing_video_404(client) -> None:
    missing = "00000000-0000-0000-0000-000000000001"
    response = client.post(f"/videos/{missing}/chat", json={"message": "hello"})
    assert response.status_code == 404


def test_chat_error_video_409(client) -> None:
    created = client.post(
        "/videos",
        files={"file": ("junk.mp4", b"not a media file" * 32, "video/mp4")},
    ).json()
    response = client.post(
        f"/videos/{created['id']}/chat",
        json={"message": "what happens at 0:10?"},
    )
    assert response.status_code == 409


def test_loop_invalid_json_retries_then_fails(tiny_mp4: Path) -> None:
    class RawBrain:
        def complete(self, messages):
            return "nope"

    try:
        run_loop(tiny_mp4, "what happens at 0:10?", RawBrain())
        raise AssertionError("expected LoopError")
    except LoopError as exc:
        assert "JSON" in str(exc)


def test_loop_stitches_if_parse_fails_after_a_look(tiny_mp4: Path) -> None:
    class Flaky:
        def __init__(self) -> None:
            self.n = 0

        def complete(self, messages: list) -> str:
            self.n += 1
            if self.n == 1:
                return (
                    '{"do":"look","start_s":0.1,"end_s":0.3,"fps":1,'
                    '"query":null,"answer":null,"times":[]}'
                )
            return "not-json"

    result = run_loop(tiny_mp4, "what is on screen?", Flaky())
    assert result.answer
    assert any(step.do == "look" and step.ok for step in result.steps)
    assert result.steps[-1].do == "answer"


def test_loop_answers_after_max_rounds_instead_of_422(tiny_mp4: Path) -> None:
    looks = [
        {
            "do": "look",
            "start_s": 0.1,
            "end_s": 0.3,
            "fps": 1,
            "query": None,
            "answer": None,
            "times": [],
        }
        for _ in range(8)
    ]
    result = run_loop(tiny_mp4, "what is on screen?", FakeBrain(looks))
    assert result.answer
    assert "look" in result.answer.lower() or "found" in result.answer.lower()
    assert result.steps[-1].do == "answer"
    assert any(step.do == "look" and step.ok for step in result.steps)


def test_vllm_brain_retries_503_then_returns(monkeypatch) -> None:
    calls = {"n": 0}

    class Boom(Exception):
        status_code = 503

    class FakeResponse:
        class Choice:
            class Message:
                content = (
                    '{"do":"answer","start_s":null,"end_s":null,'
                    '"fps":null,"answer":"ok","times":[]}'
                )

            message = Message()

        choices = [Choice()]

    class FakeCompletions:
        def create(self, **kwargs):
            calls["n"] += 1
            if calls["n"] < 3:
                raise Boom("cold")
            return FakeResponse()

    class FakeChat:
        completions = FakeCompletions()

    class FakeOpenAI:
        def __init__(self, **_kwargs) -> None:
            self.chat = FakeChat()

    monkeypatch.setattr("openai.OpenAI", FakeOpenAI)
    monkeypatch.setattr("app.agent.client.time.sleep", lambda _s: None)
    from app.settings import Settings

    brain = VllmBrain(
        Settings(
            database_url="postgresql+psycopg://video:video@127.0.0.1:5432/video_test",
            vllm_base_url="http://vllm.example/v1",
            vllm_model="google/gemma-4-E4B-it",
        )
    )
    text = brain.complete([{"role": "user", "content": "hi"}])
    assert "ok" in text
    assert calls["n"] == 3


def test_vllm_brain_uses_json_schema_not_tools(monkeypatch) -> None:
    captured: dict = {}

    class FakeResponse:
        class Choice:
            class Message:
                content = (
                    '{"do":"answer","start_s":null,"end_s":null,'
                    '"fps":null,"answer":"ok","times":[]}'
                )

            message = Message()

        choices = [Choice()]

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return FakeResponse()

    class FakeChat:
        completions = FakeCompletions()

    class FakeOpenAI:
        def __init__(self, **_kwargs) -> None:
            self.chat = FakeChat()

    monkeypatch.setattr("openai.OpenAI", FakeOpenAI)
    from app.settings import Settings

    brain = VllmBrain(
        Settings(
            database_url="postgresql+psycopg://video:video@127.0.0.1:5432/video_test",
            vllm_base_url="http://vllm.example/v1",
            vllm_model="google/gemma-4-E4B-it",
        )
    )
    text = brain.complete([{"role": "user", "content": "hi"}])
    assert "ok" in text
    assert "tools" not in captured
    assert captured["response_format"] == RESPONSE_FORMAT


def test_parse_action_accepts_look() -> None:
    action = parse_action(
        '{"do":"look","start_s":10,"end_s":14,"fps":2,"answer":null,"times":[]}'
    )
    assert action.do == "look"
    assert action.start_s == 10


def test_speech_hits_say_try_another_move(tiny_mp4: Path) -> None:
    from app.models import IndexStatus
    from app.search.transcript import TranscriptHit

    calls = {"n": 0}

    def search(_query: str) -> list[TranscriptHit]:
        calls["n"] += 1
        return [TranscriptHit(t=0.0, text="The pro plan is $99 a month.")]

    brain = FakeBrain(
        [
            {
                "do": "search",
                "start_s": None,
                "end_s": None,
                "fps": None,
                "query": None,
                "answer": None,
                "times": [],
            },
            {
                "do": "answer",
                "start_s": None,
                "end_s": None,
                "fps": None,
                "query": None,
                "answer": "They said $99 a month.",
                "times": [0.0],
            },
        ]
    )
    run_loop(
        tiny_mp4,
        "what are we supposed to ship this quarter?",
        brain,
        search=search,
        transcript_status=IndexStatus.ready.value,
    )
    observe = brain.calls[1][-1]["content"]
    assert "only what was said" in observe
    assert "Do not search spoken words again" in observe
    assert calls["n"] == 1


def test_second_speech_search_is_blocked(tiny_mp4: Path) -> None:
    from app.models import IndexStatus
    from app.search.transcript import TranscriptHit

    calls = {"n": 0}

    def search(_query: str) -> list[TranscriptHit]:
        calls["n"] += 1
        return [TranscriptHit(t=0.0, text="The pro plan is $99 a month.")]

    brain = FakeBrain(
        [
            {
                "do": "search",
                "start_s": None,
                "end_s": None,
                "fps": None,
                "query": None,
                "answer": None,
                "times": [],
            },
            {
                "do": "search",
                "start_s": None,
                "end_s": None,
                "fps": None,
                "query": "ship",
                "answer": None,
                "times": [],
            },
            {
                "do": "answer",
                "start_s": None,
                "end_s": None,
                "fps": None,
                "query": None,
                "answer": "Not in what they said.",
                "times": [],
            },
        ]
    )
    result = run_loop(
        tiny_mp4,
        "what are we supposed to ship this quarter?",
        brain,
        search=search,
        transcript_status=IndexStatus.ready.value,
    )
    assert calls["n"] == 1
    assert any(
        step.do == "search" and step.ok is False and "already" in step.detail
        for step in result.steps
    )
    blocked = brain.calls[2][-1]["content"]
    assert "already searched what was said" in blocked
    assert "Do not search spoken words again" in blocked


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


def test_empty_refusal_is_bounced_once(tiny_mp4: Path) -> None:
    brain = FakeBrain(
        [
            _act("answer", answer="I am sorry, but I cannot walk through the tape."),
            _act("look", start_s=0.1, end_s=0.3, fps=1),
            _act("answer", answer="A dark frame at the start."),
        ]
    )
    result = run_loop(tiny_mp4, "walk through the whole tape", brain)
    assert any(step.do == "look" and step.ok for step in result.steps)
    assert result.answer == "A dark frame at the start."
    nudge = brain.calls[1][-1]["content"]
    assert "Do not answer yet" in nudge
    assert "Do not only apologize" in nudge


def test_empty_promise_is_bounced_once(tiny_mp4: Path) -> None:
    brain = FakeBrain(
        [
            _act("answer", answer="I will provide a sequential walkthrough of the video."),
            _act("look", start_s=0.1, end_s=0.3, fps=1),
            _act("answer", answer="A dark frame at the start."),
        ]
    )
    result = run_loop(tiny_mp4, "walk through the whole tape", brain)
    assert any(step.do == "look" and step.ok for step in result.steps)
    assert result.answer == "A dark frame at the start."
    nudge = brain.calls[1][-1]["content"]
    assert "Do not answer yet" in nudge


def test_empty_parse_retries_once_then_looks(tiny_mp4: Path) -> None:
    class EventuallyJson:
        def __init__(self) -> None:
            self.n = 0

        def complete(self, messages: list) -> str:
            self.n += 1
            if self.n <= 2:
                return "nope"
            if self.n == 3:
                return (
                    '{"do":"look","start_s":0.1,"end_s":0.3,"fps":1,'
                    '"query":null,"answer":null,"times":[]}'
                )
            return (
                '{"do":"answer","start_s":null,"end_s":null,"fps":null,'
                '"query":null,"answer":"A dark frame.","times":[0.1]}'
            )

    result = run_loop(tiny_mp4, "what is on screen?", EventuallyJson())
    assert result.answer == "A dark frame."
    assert any(step.do == "look" and step.ok for step in result.steps)


def test_second_slide_search_is_blocked(tiny_mp4: Path) -> None:
    import uuid

    from app.models import IndexStatus
    from app.search.slides import SlideHit

    calls = {"n": 0}

    def search(_query: str) -> list[SlideHit]:
        calls["n"] += 1
        return [
            SlideHit(
                t=0.1,
                t_end=0.4,
                score=0.9,
                slide_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            ),
            SlideHit(
                t=0.5,
                t_end=0.9,
                score=0.8,
                slide_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            ),
        ]

    brain = FakeBrain(
        [
            _act("search_slides"),
            _act("search_slides", query="again"),
            _act("look", start_s=0.1, end_s=0.3, fps=1),
            _act("answer", answer="Dark frame."),
        ]
    )
    result = run_loop(
        tiny_mp4,
        "what color is the printed number?",
        brain,
        search_slides=search,
        slides_status=IndexStatus.ready.value,
    )
    assert calls["n"] == 1
    assert any(
        step.do == "search_slides" and step.ok is False and "already" in step.detail
        for step in result.steps
    )
    blocked = brain.calls[2][-1]["content"]
    assert "already searched printed slides" in blocked
    assert "0.5s" in blocked


def test_repeat_look_is_blocked_and_names_unused_slide(tiny_mp4: Path) -> None:
    import uuid

    from app.models import IndexStatus
    from app.search.slides import SlideHit

    def search(_query: str) -> list[SlideHit]:
        return [
            SlideHit(
                t=0.1,
                t_end=0.4,
                score=0.9,
                slide_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            ),
            SlideHit(
                t=0.5,
                t_end=0.9,
                score=0.8,
                slide_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            ),
        ]

    brain = FakeBrain(
        [
            _act("search_slides"),
            _act("look", start_s=0.1, end_s=0.3, fps=1),
            _act("look", start_s=0.1, end_s=0.3, fps=1),
            _act("look", start_s=0.5, end_s=0.7, fps=1),
            _act("answer", answer="I looked at both listed times."),
        ]
    )
    result = run_loop(
        tiny_mp4,
        "what color is the printed number?",
        brain,
        search_slides=search,
        slides_status=IndexStatus.ready.value,
    )
    assert any(
        step.do == "look" and step.ok is False and "already" in step.detail
        for step in result.steps
    )
    assert sum(1 for step in result.steps if step.do == "look" and step.ok) == 2
    blocked = next(
        call[-1]["content"]
        for call in brain.calls
        if isinstance(call[-1].get("content"), str)
        and "already looked near" in call[-1]["content"]
    )
    assert "0.5s" in blocked
    after = next(
        call[-1]["content"]
        for call in brain.calls
        if isinstance(call[-1].get("content"), str)
        and "next unused slide time" in call[-1]["content"]
    )
    assert "0.5s" in after
