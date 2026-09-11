from __future__ import annotations

from pathlib import Path

from app.agent.client import FakeBrain
from app.agent.schema import parse_action
from app.ingest.whisper import TranscriptSegment
from app.main import app
from app.models import IndexStatus, TranscriptLine, Video
from app.routes.chat import get_brain
from app.search.embed import EMBED_DIM, FakeEmbedder
from app.search.transcript import TOP_HITS, search_transcript
from sqlmodel import Session, select


INGEST_SECRET = "test-ingest-secret"


def _upload(client, path: Path):
    with path.open("rb") as handle:
        return client.post(
            "/videos",
            files={"file": (path.name, handle, "application/octet-stream")},
        )


def _axis(index: int) -> list[float]:
    vector = [0.0] * EMBED_DIM
    vector[index] = 1.0
    return vector


def _plant(
    session: Session,
    video_id,
    start_s: float,
    text: str,
    embedding: list[float] | None = None,
) -> None:
    session.add(
        TranscriptLine(
            video_id=video_id,
            start_s=start_s,
            end_s=start_s + 1.0,
            text=text,
            embedding=embedding if embedding is not None else _axis(0),
        )
    )
    session.commit()


def _override(brain: FakeBrain) -> None:
    app.dependency_overrides[get_brain] = lambda: brain


def _clear_override() -> None:
    app.dependency_overrides.pop(get_brain, None)


def test_upload_response_does_not_wait_for_whisper(client, tiny_mp4: Path) -> None:
    created = _upload(client, tiny_mp4).json()
    assert created["status"] == "ready"
    assert created["transcript_status"] == IndexStatus.processing.value
    detail = client.get(f"/videos/{created['id']}").json()
    assert detail["transcript_status"] == IndexStatus.ready.value


def test_keyword_pricing_surfaces_a_time(client, tiny_mp4: Path) -> None:
    from app.db import get_engine

    video_id = _upload(client, tiny_mp4).json()["id"]
    engine = get_engine()
    with Session(engine) as session:
        video = session.get(Video, video_id)
        assert video is not None
        _plant(session, video.id, 12.4, "Our pricing starts at nine dollars")
        hits = search_transcript(session, video.id, "pricing", FakeEmbedder())
    assert hits
    assert any(abs(hit.t - 12.4) < 0.01 for hit in hits)
    assert any("pricing" in hit.text.lower() for hit in hits)


def test_paraphrase_surfaces_planted_neighbor(client, tiny_mp4: Path) -> None:
    from app.db import get_engine

    video_id = _upload(client, tiny_mp4).json()["id"]
    target = _axis(1)
    other = _axis(2)
    query = "how much does it cost?"
    near = list(target)
    near[1] = 0.99
    near[2] = 0.01
    engine = get_engine()
    with Session(engine) as session:
        video = session.get(Video, video_id)
        assert video is not None
        _plant(session, video.id, 40.0, "tickets are nine dollars each", target)
        _plant(session, video.id, 1.0, "we opened with the weather report", other)
        embedder = FakeEmbedder(query_vectors={query: near})
        hits = search_transcript(session, video.id, query, embedder)
    assert hits
    assert abs(hits[0].t - 40.0) < 0.01
    assert "tickets" in hits[0].text


def test_second_question_does_not_run_whisper(
    client, tiny_mp4: Path, monkeypatch
) -> None:
    calls: list[Path] = []

    def counting(wav_path: Path, model_name: str = "turbo") -> list[TranscriptSegment]:
        calls.append(wav_path)
        return [TranscriptSegment(0.0, 1.0, "hello there")]

    monkeypatch.setattr("app.ingest.whisper.transcribe_wav", counting)
    video_id = _upload(client, tiny_mp4).json()["id"]
    assert len(calls) == 1
    brain = FakeBrain(
        [
            {
                "do": "look",
                "start_s": 0.1,
                "end_s": 0.3,
                "fps": 1,
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
                "answer": "First.",
                "times": [],
            },
            {
                "do": "look",
                "start_s": 0.1,
                "end_s": 0.3,
                "fps": 1,
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
                "answer": "Second.",
                "times": [],
            },
        ]
    )
    _override(brain)
    try:
        first = client.post(
            f"/videos/{video_id}/chat", json={"message": "what did they say?"}
        )
        second = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "say it again", "session_id": first.json()["session_id"]},
        )
    finally:
        _clear_override()
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert len(calls) == 1


def test_look_works_while_transcript_processing(
    client, tiny_mp4: Path, monkeypatch
) -> None:
    monkeypatch.setattr("app.ingest.speech.ingest_video", lambda *_a, **_k: None)
    created = _upload(client, tiny_mp4).json()
    assert created["status"] == "ready"
    assert created["transcript_status"] == IndexStatus.processing.value
    brain = FakeBrain(
        [
            {
                "do": "look",
                "start_s": 0.1,
                "end_s": 0.5,
                "fps": 2,
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
                "answer": "A dark frame.",
                "times": [0.1],
            },
        ]
    )
    _override(brain)
    try:
        response = client.post(
            f"/videos/{created['id']}/chat",
            json={"message": "what happens at 0:10?"},
        )
    finally:
        _clear_override()
    assert response.status_code == 200, response.text
    assert response.json()["steps"][0]["do"] == "look"
    assert response.json()["steps"][0]["ok"] is True


def test_search_while_processing_does_not_dump_lines(
    client, tiny_mp4: Path, monkeypatch
) -> None:
    monkeypatch.setattr("app.ingest.speech.ingest_video", lambda *_a, **_k: None)
    video_id = _upload(client, tiny_mp4).json()["id"]
    brain = FakeBrain(
        [
            {
                "do": "search",
                "start_s": None,
                "end_s": None,
                "fps": None,
                "query": "pricing",
                "answer": None,
                "times": [],
            },
            {
                "do": "answer",
                "start_s": None,
                "end_s": None,
                "fps": None,
                "query": None,
                "answer": "Transcript is still running.",
                "times": [],
            },
        ]
    )
    _override(brain)
    try:
        response = client.post(
            f"/videos/{video_id}/chat", json={"message": "pricing?"}
        )
    finally:
        _clear_override()
    assert response.status_code == 200, response.text
    observe = brain.calls[1][-1]["content"]
    assert "not ready" in observe
    assert "whole file" not in observe.lower() or "not" in observe.lower()


def test_search_does_not_dump_whole_transcript(client, tiny_mp4: Path) -> None:
    from app.db import get_engine

    video_id = _upload(client, tiny_mp4).json()["id"]
    tokens = [f"uniq_{i:03d}" for i in range(20)]
    engine = get_engine()
    with Session(engine) as session:
        video = session.get(Video, video_id)
        assert video is not None
        for i, token in enumerate(tokens):
            _plant(session, video.id, float(i), f"meeting notes {token}")
    brain = FakeBrain(
        [
            {
                "do": "search",
                "start_s": None,
                "end_s": None,
                "fps": None,
                "query": "meeting",
                "answer": None,
                "times": [],
            },
            {
                "do": "answer",
                "start_s": None,
                "end_s": None,
                "fps": None,
                "query": None,
                "answer": "They talked about the meeting.",
                "times": [0.0],
            },
        ]
    )
    _override(brain)
    try:
        response = client.post(
            f"/videos/{video_id}/chat", json={"message": "what about the meeting?"}
        )
    finally:
        _clear_override()
    assert response.status_code == 200, response.text
    observe = brain.calls[1][-1]["content"]
    assert "not the whole file" in observe
    present = sum(1 for token in tokens if token in observe)
    assert 1 <= present <= TOP_HITS
    assert present < len(tokens)


def test_ingest_does_not_use_capped_get_audio(
    client, tiny_mp4: Path, monkeypatch
) -> None:
    def boom(*_args, **_kwargs):
        raise AssertionError("ingest must not use get_audio")

    monkeypatch.setattr("app.tools.audio.get_audio", boom)
    created = _upload(client, tiny_mp4).json()
    assert client.get(f"/videos/{created['id']}").json()["transcript_status"] == "ready"


def test_no_audio_is_skipped(client, media_dir: Path) -> None:
    path = media_dir / "silent.mp4"
    import subprocess

    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=64x64:d=1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    created = _upload(client, path).json()
    assert created["status"] == "ready"
    assert created["transcript_status"] == IndexStatus.skipped.value
    assert created["has_audio"] is False


def test_probe_error_skips_transcript(client) -> None:
    created = client.post(
        "/videos",
        files={"file": ("junk.mp4", b"not a media file" * 32, "video/mp4")},
    ).json()
    assert created["status"] == "error"
    assert created["transcript_status"] == IndexStatus.skipped.value


def test_internal_transcript_callback(client, tiny_mp4: Path, monkeypatch) -> None:
    from app.db import get_engine

    monkeypatch.setattr("app.ingest.speech.ingest_video", lambda *_a, **_k: None)
    video_id = _upload(client, tiny_mp4).json()["id"]
    denied = client.post(
        f"/internal/videos/{video_id}/transcript",
        json={
            "status": "ready",
            "segments": [{"start_s": 5.0, "end_s": 6.0, "text": "pricing later"}],
        },
    )
    assert denied.status_code == 403
    accepted = client.post(
        f"/internal/videos/{video_id}/transcript",
        headers={"Authorization": f"Bearer {INGEST_SECRET}"},
        json={
            "status": "ready",
            "segments": [{"start_s": 5.0, "end_s": 6.0, "text": "pricing later"}],
        },
    )
    assert accepted.status_code == 200, accepted.text
    engine = get_engine()
    with Session(engine) as session:
        video = session.get(Video, video_id)
        assert video is not None
        assert video.transcript_status == IndexStatus.ready.value
        rows = session.exec(
            select(TranscriptLine).where(TranscriptLine.video_id == video.id)
        ).all()
        assert len(rows) == 1
        assert "pricing" in rows[0].text
    ignored = client.post(
        f"/internal/videos/{video_id}/transcript",
        headers={"Authorization": f"Bearer {INGEST_SECRET}"},
        json={
            "status": "ready",
            "segments": [{"start_s": 9.0, "end_s": 10.0, "text": "should ignore"}],
        },
    )
    assert ignored.json().get("ignored") is True
    with Session(engine) as session:
        still = session.exec(
            select(TranscriptLine).where(TranscriptLine.video_id == video_id)
        ).all()
        assert len(still) == 1
        assert "should ignore" not in still[0].text


def test_delete_video_removes_transcript_lines(client, tiny_mp4: Path) -> None:
    from app.db import get_engine

    video_id = _upload(client, tiny_mp4).json()["id"]
    engine = get_engine()
    with Session(engine) as session:
        video = session.get(Video, video_id)
        assert video is not None
        _plant(session, video.id, 1.0, "pricing")
    assert client.delete(f"/videos/{video_id}").status_code == 204
    with Session(engine) as session:
        leftover = session.exec(select(TranscriptLine)).all()
        assert leftover == []


def test_parse_action_accepts_search() -> None:
    action = parse_action(
        '{"do":"search","start_s":null,"end_s":null,"fps":null,'
        '"query":"pricing","answer":null,"times":[]}'
    )
    assert action.do == "search"
    assert action.query == "pricing"


def test_search_missing_query_uses_user_question(tiny_mp4: Path) -> None:
    from app.agent.loop import run_loop
    from app.search.transcript import TranscriptHit

    seen: list[str] = []

    def search(query: str) -> list[TranscriptHit]:
        seen.append(query)
        return [TranscriptHit(t=12.4, text="Our pricing starts at nine dollars")]

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
                "answer": "About nine dollars.",
                "times": [12.4],
            },
        ]
    )
    result = run_loop(
        tiny_mp4,
        "what about pricing?",
        brain,
        search=search,
        transcript_status=IndexStatus.ready.value,
    )
    assert seen == ["what about pricing?"]
    observe = brain.calls[1][-1]["content"]
    assert "12.4" in observe
    assert "pricing" in observe.lower()
    assert result.citations == [12.4]
