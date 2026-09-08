from __future__ import annotations

from pathlib import Path

from sqlmodel import Session, select

from app.agent.client import FakeBrain
from app.agent.loop import Step
from app.agent.memory import TimeWindow, collect_windows, push_windows
from app.main import app
from app.models import ChatSession, Video
from app.routes.chat import get_brain
from app.search.transcript import search_transcript


def _upload(client, path: Path):
    with path.open("rb") as handle:
        return client.post(
            "/videos",
            files={"file": (path.name, handle, "application/octet-stream")},
        )


def _act(do: str, **kwargs):
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


def _look(start_s: float, end_s: float) -> dict:
    return _act("look", start_s=start_s, end_s=end_s, fps=2)


def _answer(text: str, times: list[float] | None = None) -> dict:
    return _act("answer", answer=text, times=times or [])


def _override(brain: FakeBrain) -> None:
    app.dependency_overrides[get_brain] = lambda: brain


def _clear_override() -> None:
    app.dependency_overrides.pop(get_brain, None)


def _user_text(messages: list[dict]) -> str:
    for message in messages:
        if message.get("role") == "user":
            content = message.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                texts = [
                    part.get("text", "")
                    for part in content
                    if isinstance(part, dict) and part.get("type") == "text"
                ]
                return " ".join(texts)
    return ""


def _has_media_parts(messages: list[dict]) -> bool:
    for message in messages:
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") in {"image_url", "input_audio"}:
                return True
    return False


def test_push_windows_keeps_last_three() -> None:
    first = TimeWindow(0.0, 0.2, "look")
    second = TimeWindow(0.2, 0.3, "look")
    third = TimeWindow(0.3, 0.4, "listen")
    fourth = TimeWindow(0.4, 0.5, "export_clip")
    kept = push_windows([], [first, second, third, fourth])
    assert [item["kind"] for item in kept] == ["look", "listen", "export_clip"]
    assert kept[0]["start_s"] == 0.2
    failed = collect_windows(
        [Step(do="look", start_s=0.0, end_s=1.0, ok=False), Step(do="answer", ok=True)]
    )
    assert failed == []


def test_followup_that_frame_uses_last_times(client, tiny_mp4: Path) -> None:
    from app.db import get_engine

    video_id = _upload(client, tiny_mp4).json()["id"]
    brain = FakeBrain(
        [
            _look(0.1, 0.5),
            _answer("A dark frame at 0.1s.", [0.1]),
            _answer("No car in that frame.", [0.1]),
        ]
    )
    _override(brain)
    try:
        first = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "what happens at the start?"},
        )
        assert first.status_code == 200, first.text
        session_id = first.json()["session_id"]
        second = client.post(
            f"/videos/{video_id}/chat",
            json={
                "message": "was a car in that frame?",
                "session_id": session_id,
            },
        )
    finally:
        _clear_override()
    assert second.status_code == 200, second.text
    body = second.json()
    assert body["session_id"] == session_id
    assert body["answer"] == "No car in that frame."
    assert len(brain.calls) == 3
    follow = brain.calls[2]
    text = _user_text(follow)
    assert "Last time windows" in text
    assert "that frame" in text
    assert "look 0.10s–0.50s" in text
    assert "what happens at the start?" in text
    assert "A dark frame at 0.1s." in text
    assert "was a car in that frame?" in text
    assert "not attached" in text
    assert _has_media_parts(follow) is False
    engine = get_engine()
    with Session(engine) as db:
        chat = db.get(ChatSession, session_id)
        assert chat is not None
        assert len(chat.last_times) == 1
        assert chat.last_times[0]["kind"] == "look"


def test_followup_look_attaches_new_frames_not_old_ones(client, tiny_mp4: Path) -> None:
    video_id = _upload(client, tiny_mp4).json()["id"]
    brain = FakeBrain(
        [
            _look(0.1, 0.5),
            _answer("A dark frame at 0.1s.", [0.1]),
            _look(0.1, 0.5),
            _answer("Still dark. No car.", [0.1]),
        ]
    )
    _override(brain)
    try:
        session_id = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "what happens at the start?"},
        ).json()["session_id"]
        response = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "look at that frame again", "session_id": session_id},
        )
    finally:
        _clear_override()
    assert response.status_code == 200, response.text
    assert _has_media_parts(brain.calls[2]) is False
    assert _has_media_parts(brain.calls[3]) is True
    observe = brain.calls[3][-1]
    parts = observe["content"]
    assert any(part.get("type") == "image_url" for part in parts)
    assert "data:image" not in _user_text(brain.calls[2])


def test_followup_does_not_search_from_scratch(client, tiny_mp4: Path, monkeypatch) -> None:
    def boom(*_args, **_kwargs):
        raise AssertionError("search must not run when last_times already exist")

    video_id = _upload(client, tiny_mp4).json()["id"]
    brain = FakeBrain(
        [
            _look(0.1, 0.5),
            _answer("A dark frame at 0.1s.", [0.1]),
            _answer("No car in that frame.", [0.1]),
        ]
    )
    _override(brain)
    try:
        session_id = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "what happens at the start?"},
        ).json()["session_id"]
        monkeypatch.setattr(
            "app.routes.chat.search_transcript",
            boom,
        )
        monkeypatch.setattr(
            "app.search.transcript.search_transcript",
            boom,
        )
        response = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "was a car in that frame?", "session_id": session_id},
        )
    finally:
        _clear_override()
    assert response.status_code == 200, response.text
    assert "Last time windows" in _user_text(brain.calls[2])
    assert search_transcript is not boom


def test_second_turn_does_not_reingest(client, tiny_mp4: Path, monkeypatch) -> None:
    import app.ingest.speech as speech
    import app.ingest.sound as sound
    import app.ingest.visual as visual

    counts = {"speech": 0, "visual": 0, "sound": 0}
    real_speech = speech.ingest_video
    real_visual = visual.ingest_visual
    real_sound = sound.ingest_sound

    def wrap_speech(*args, **kwargs):
        counts["speech"] += 1
        return real_speech(*args, **kwargs)

    def wrap_visual(*args, **kwargs):
        counts["visual"] += 1
        return real_visual(*args, **kwargs)

    def wrap_sound(*args, **kwargs):
        counts["sound"] += 1
        return real_sound(*args, **kwargs)

    monkeypatch.setattr(speech, "ingest_video", wrap_speech)
    monkeypatch.setattr(visual, "ingest_visual", wrap_visual)
    monkeypatch.setattr(sound, "ingest_sound", wrap_sound)
    video_id = _upload(client, tiny_mp4).json()["id"]
    after_upload = dict(counts)
    assert after_upload["speech"] >= 1
    assert after_upload["visual"] >= 1
    assert after_upload["sound"] >= 1
    brain = FakeBrain(
        [
            _look(0.1, 0.5),
            _answer("A dark frame at 0.1s.", [0.1]),
            _answer("No car in that frame.", [0.1]),
        ]
    )
    _override(brain)
    try:
        session_id = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "what happens at the start?"},
        ).json()["session_id"]
        client.post(
            f"/videos/{video_id}/chat",
            json={"message": "was a car in that frame?", "session_id": session_id},
        )
    finally:
        _clear_override()
    assert counts == after_upload
    detail = client.get(f"/videos/{video_id}").json()
    assert detail["status"] == "ready"


def test_new_session_starts_clean(client, tiny_mp4: Path) -> None:
    video_id = _upload(client, tiny_mp4).json()["id"]
    brain = FakeBrain(
        [
            _look(0.1, 0.5),
            _answer("First thread.", [0.1]),
            _look(0.1, 0.5),
            _answer("Second thread.", [0.1]),
        ]
    )
    _override(brain)
    try:
        first = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "what happens at the start?"},
        ).json()
        second = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "another question"},
        ).json()
    finally:
        _clear_override()
    assert first["session_id"] != second["session_id"]
    follow = _user_text(brain.calls[2])
    assert "Last time windows" not in follow
    assert "what happens at the start?" not in follow
    assert "First thread." not in follow
    assert "another question" in follow


def test_keeps_last_three_windows(client, tiny_mp4: Path) -> None:
    from app.db import get_engine

    video_id = _upload(client, tiny_mp4).json()["id"]
    brain = FakeBrain(
        [
            _look(0.05, 0.15),
            _look(0.15, 0.25),
            _look(0.25, 0.35),
            _look(0.35, 0.45),
            _answer("Four looks.", [0.35]),
        ]
    )
    _override(brain)
    try:
        body = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "scan a few windows"},
        ).json()
    finally:
        _clear_override()
    engine = get_engine()
    with Session(engine) as db:
        chat = db.get(ChatSession, body["session_id"])
        assert chat is not None
        assert len(chat.last_times) == 3
        starts = [item["start_s"] for item in chat.last_times]
        assert starts == [0.15, 0.25, 0.35]


def test_session_from_other_video_404(client, tiny_mp4: Path, tiny_audio: Path) -> None:
    first = _upload(client, tiny_mp4).json()["id"]
    second = _upload(client, tiny_audio).json()["id"]
    brain = FakeBrain([_look(0.1, 0.5), _answer("ok", [0.1])])
    _override(brain)
    try:
        session_id = client.post(
            f"/videos/{first}/chat",
            json={"message": "what happens at the start?"},
        ).json()["session_id"]
        response = client.post(
            f"/videos/{second}/chat",
            json={"message": "was a car in that frame?", "session_id": session_id},
        )
    finally:
        _clear_override()
    assert response.status_code == 404


def test_delete_video_still_removes_sessions(client, tiny_mp4: Path) -> None:
    from app.db import get_engine

    video_id = _upload(client, tiny_mp4).json()["id"]
    _override(FakeBrain([_look(0.1, 0.5), _answer("ok", [0.1])]))
    try:
        session_id = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "what happens at the start?"},
        ).json()["session_id"]
    finally:
        _clear_override()
    assert client.delete(f"/videos/{video_id}").status_code == 204
    engine = get_engine()
    with Session(engine) as db:
        assert db.get(ChatSession, session_id) is None
        assert db.get(Video, video_id) is None
        assert db.exec(select(ChatSession)).all() == []
