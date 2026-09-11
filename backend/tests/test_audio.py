from __future__ import annotations

import re
from pathlib import Path

from app.agent.client import FakeBrain
from app.agent.loop import run_loop
from app.agent.schema import parse_action
from app.main import app
from app.models import AudioChunk, IndexStatus, Video
from app.routes.chat import get_brain
from app.search.audio import TOP_HITS, merge_clusters, search_audio
from app.search.clap import AUDIO_DIM, FakeAudioEmbedder
from app.search.audio import AudioHit
from app.storage import video_folder
from sqlmodel import Session, select


INGEST_SECRET = "test-ingest-secret"


def _upload(client, path: Path):
    with path.open("rb") as handle:
        return client.post(
            "/videos",
            files={"file": (path.name, handle, "application/octet-stream")},
        )


def _axis(index: int) -> list[float]:
    vector = [0.0] * AUDIO_DIM
    vector[index] = 1.0
    return vector


def _plant(
    session: Session,
    video_id,
    start_s: float,
    end_s: float,
    embedding: list[float],
) -> None:
    session.add(
        AudioChunk(
            video_id=video_id, start_s=start_s, end_s=end_s, embedding=embedding
        )
    )
    session.commit()


def _wipe_chunks(session: Session, video_id) -> None:
    from sqlalchemy import text

    session.execute(
        text("DELETE FROM audio_chunks WHERE video_id = :vid"),
        {"vid": video_id},
    )
    session.commit()


def _override(brain: FakeBrain) -> None:
    app.dependency_overrides[get_brain] = lambda: brain


def _clear_override() -> None:
    app.dependency_overrides.pop(get_brain, None)


def test_upload_does_not_wait_for_clap(client, tiny_mp4: Path) -> None:
    created = _upload(client, tiny_mp4).json()
    assert created["status"] == "ready"
    assert created["audio_status"] == IndexStatus.processing.value
    detail = client.get(f"/videos/{created['id']}").json()
    assert detail["audio_status"] == IndexStatus.ready.value


def test_bird_chirp_surfaces_a_time(client, tiny_mp4: Path) -> None:
    from app.db import get_engine

    video_id = _upload(client, tiny_mp4).json()["id"]
    target = _axis(0)
    other = _axis(1)
    query = "bird chirp"
    engine = get_engine()
    with Session(engine) as session:
        video = session.get(Video, video_id)
        assert video is not None
        _wipe_chunks(session, video.id)
        _plant(session, video.id, 8.0, 11.0, target)
        _plant(session, video.id, 1.0, 4.0, other)
        result = search_audio(
            session, video.id, query, FakeAudioEmbedder(query_vectors={query: target})
        )
    assert result.hits
    assert abs(result.hits[0].start_s - 8.0) < 0.01


def test_second_question_does_not_run_clap(
    client, tiny_mp4: Path, monkeypatch
) -> None:
    calls: list[int] = []

    def counting(wavs, model_name: str = ""):
        calls.append(len(wavs))
        return [[0.0] * AUDIO_DIM for _ in wavs]

    monkeypatch.setattr("app.ingest.clap.embed_wavs", counting)
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
            f"/videos/{video_id}/chat", json={"message": "when did the bird chirp?"}
        )
        second = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "again", "session_id": first.json()["session_id"]},
        )
    finally:
        _clear_override()
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert len(calls) == 1


def test_listen_works_while_audio_processing(
    client, tiny_mp4: Path, monkeypatch
) -> None:
    monkeypatch.setattr("app.ingest.sound.ingest_sound", lambda *_a, **_k: None)
    created = _upload(client, tiny_mp4).json()
    assert created["status"] == "ready"
    assert created["audio_status"] == IndexStatus.processing.value
    brain = FakeBrain(
        [
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
                "answer": "A tone.",
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
    assert response.json()["steps"][0]["do"] == "listen"
    assert response.json()["steps"][0]["ok"] is True


def test_nearby_hits_merge_to_count_one() -> None:
    hits = [
        AudioHit(start_s=1.0, end_s=4.0, score=0.9),
        AudioHit(start_s=2.5, end_s=5.5, score=0.8),
        AudioHit(start_s=4.0, end_s=7.0, score=0.7),
    ]
    clusters = merge_clusters(hits)
    assert len(clusters) == 1
    assert abs(clusters[0].start_s - 1.0) < 0.01
    assert abs(clusters[0].end_s - 7.0) < 0.01


def test_stadium_blob_is_one_span(client, tiny_mp4: Path) -> None:
    from app.db import get_engine

    video_id = _upload(client, tiny_mp4).json()["id"]
    applause = _axis(2)
    engine = get_engine()
    with Session(engine) as session:
        video = session.get(Video, video_id)
        assert video is not None
        _wipe_chunks(session, video.id)
        for i in range(12):
            start = 60.0 + i * 1.5
            _plant(session, video.id, start, start + 3.0, applause)
        result = search_audio(
            session,
            video.id,
            "applause",
            FakeAudioEmbedder(query_vectors={"applause": applause}),
        )
    assert result.count == 1
    assert abs(result.clusters[0].start_s - 60.0) < 0.01
    assert abs(result.clusters[0].end_s - 73.5) < 0.01


def test_two_claps_count_two(client, tiny_mp4: Path) -> None:
    from app.db import get_engine

    video_id = _upload(client, tiny_mp4).json()["id"]
    clap = _axis(4)
    engine = get_engine()
    with Session(engine) as session:
        video = session.get(Video, video_id)
        assert video is not None
        _wipe_chunks(session, video.id)
        _plant(session, video.id, 10.0, 13.0, clap)
        _plant(session, video.id, 40.0, 43.0, clap)
        result = search_audio(
            session,
            video.id,
            "clap",
            FakeAudioEmbedder(query_vectors={"clap": clap}),
        )
    assert result.count == 2


def test_search_audio_does_not_dump_all_times(client, tiny_mp4: Path) -> None:
    from app.db import get_engine

    video_id = _upload(client, tiny_mp4).json()["id"]
    engine = get_engine()
    with Session(engine) as session:
        video = session.get(Video, video_id)
        assert video is not None
        for i in range(20):
            vec = _axis(0 if i < 12 else 5)
            _plant(session, video.id, float(i * 10), float(i * 10 + 3), vec)
    brain = FakeBrain(
        [
            {
                "do": "search_audio",
                "start_s": None,
                "end_s": None,
                "fps": None,
                "query": "clap",
                "answer": None,
                "times": [],
            },
            {
                "do": "answer",
                "start_s": None,
                "end_s": None,
                "fps": None,
                "query": None,
                "answer": "Claps around those times.",
                "times": [0.0],
            },
        ]
    )
    _override(brain)
    try:
        response = client.post(
            f"/videos/{video_id}/chat", json={"message": "how many claps?"}
        )
    finally:
        _clear_override()
    assert response.status_code == 200, response.text
    observe = brain.calls[1][-1]["content"]
    assert "not the whole file" in observe
    assert "times to listen" in observe
    assert "count=" not in observe
    assert "middle=" in observe
    assert "count is zero" in observe
    assert len(re.findall(r"\[\d+\.\d+s–", observe)) <= TOP_HITS


def test_ingest_does_not_use_capped_get_audio(
    client, tiny_mp4: Path, monkeypatch
) -> None:
    def boom(*_args, **_kwargs):
        raise AssertionError("ingest must not use get_audio")

    monkeypatch.setattr("app.tools.audio.get_audio", boom)
    created = _upload(client, tiny_mp4).json()
    assert client.get(f"/videos/{created['id']}").json()["audio_status"] == "ready"


def test_index_wavs_deleted_after_ingest(client, tiny_mp4: Path, data_dir: Path) -> None:
    created = _upload(client, tiny_mp4).json()
    folder = video_folder(data_dir, created["id"])
    assert not (folder / "ingest_chunks").exists()
    leftover = list(folder.glob("*.wav"))
    assert leftover == []
    assert not (folder / "clap.wav").exists()
    assert not (folder / "ingest_chunks.tar").exists()


def test_mute_skips_audio(client, tiny_mute: Path) -> None:
    created = _upload(client, tiny_mute).json()
    assert created["status"] == "ready"
    assert created["has_audio"] is True
    detail = client.get(f"/videos/{created['id']}").json()
    assert detail["audio_status"] == IndexStatus.skipped.value


def test_video_only_skips_audio(client, tiny_video_only: Path) -> None:
    created = _upload(client, tiny_video_only).json()
    assert created["status"] == "ready"
    assert created["has_audio"] is False
    assert created["audio_status"] == IndexStatus.skipped.value


def test_probe_error_skips_audio(client) -> None:
    created = client.post(
        "/videos",
        files={"file": ("junk.mp4", b"not a media file" * 32, "video/mp4")},
    ).json()
    assert created["status"] == "error"
    assert created["audio_status"] == IndexStatus.skipped.value


def test_internal_sound_callback(client, tiny_mp4: Path, monkeypatch) -> None:
    from app.db import get_engine

    monkeypatch.setattr("app.ingest.sound.ingest_sound", lambda *_a, **_k: None)
    video_id = _upload(client, tiny_mp4).json()["id"]
    denied = client.post(
        f"/internal/videos/{video_id}/sound",
        json={
            "status": "ready",
            "chunks": [
                {"start_s": 3.0, "end_s": 6.0, "embedding": _axis(0)}
            ],
        },
    )
    assert denied.status_code == 403
    accepted = client.post(
        f"/internal/videos/{video_id}/sound",
        headers={"Authorization": f"Bearer {INGEST_SECRET}"},
        json={
            "status": "ready",
            "chunks": [
                {"start_s": 3.0, "end_s": 6.0, "embedding": _axis(0)}
            ],
        },
    )
    assert accepted.status_code == 200, accepted.text
    engine = get_engine()
    with Session(engine) as session:
        video = session.get(Video, video_id)
        assert video is not None
        assert video.audio_status == IndexStatus.ready.value
        rows = session.exec(
            select(AudioChunk).where(AudioChunk.video_id == video.id)
        ).all()
        assert len(rows) == 1
        assert abs(rows[0].start_s - 3.0) < 0.01
    ignored = client.post(
        f"/internal/videos/{video_id}/sound",
        headers={"Authorization": f"Bearer {INGEST_SECRET}"},
        json={
            "status": "ready",
            "chunks": [
                {"start_s": 9.0, "end_s": 12.0, "embedding": _axis(1)}
            ],
        },
    )
    assert ignored.json().get("ignored") is True
    with Session(engine) as session:
        still = session.exec(
            select(AudioChunk).where(AudioChunk.video_id == video_id)
        ).all()
        assert len(still) == 1


def test_delete_video_removes_audio_chunks(client, tiny_mp4: Path) -> None:
    from app.db import get_engine

    video_id = _upload(client, tiny_mp4).json()["id"]
    engine = get_engine()
    with Session(engine) as session:
        video = session.get(Video, video_id)
        assert video is not None
        _plant(session, video.id, 1.0, 4.0, _axis(0))
    assert client.delete(f"/videos/{video_id}").status_code == 204
    with Session(engine) as session:
        leftover = session.exec(select(AudioChunk)).all()
        assert leftover == []


def test_parse_action_accepts_search_audio() -> None:
    action = parse_action(
        '{"do":"search_audio","start_s":null,"end_s":null,"fps":null,'
        '"query":"bird chirp","answer":null,"times":[]}'
    )
    assert action.do == "search_audio"
    assert action.query == "bird chirp"


def test_search_audio_missing_query_uses_user_question(tiny_mp4: Path) -> None:
    from app.search.audio import AudioSearchResult

    seen: list[str] = []

    def search(query: str) -> AudioSearchResult:
        seen.append(query)
        hit = AudioHit(start_s=8.0, end_s=11.0, score=0.9)
        return AudioSearchResult(hits=[hit], clusters=merge_clusters([hit]), count=1)

    brain = FakeBrain(
        [
            {
                "do": "search_audio",
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
                "answer": "A chirp at eight seconds.",
                "times": [8.0],
            },
        ]
    )
    result = run_loop(
        tiny_mp4,
        "when did the bird chirp?",
        brain,
        search_audio=search,
        audio_status=IndexStatus.ready.value,
        visual_status=IndexStatus.ready.value,
        transcript_status=IndexStatus.ready.value,
    )
    assert seen == ["when did the bird chirp?"]
    observe = brain.calls[1][-1]["content"]
    assert "8.0" in observe
    assert "times to listen" in observe
    assert "middle=" in observe
    assert "count=" not in observe
    assert result.citations == [8.0]
