from __future__ import annotations

import re
from pathlib import Path

from app.agent.client import FakeBrain
from app.agent.loop import run_loop
from app.agent.schema import parse_action
from app.main import app
from app.models import IndexStatus, Video, VisualFrame
from app.routes.chat import get_brain
from app.search.siglip import VISUAL_DIM, FakeVisualEmbedder
from app.search.visual import TOP_HITS, search_visual
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
    vector = [0.0] * VISUAL_DIM
    vector[index] = 1.0
    return vector


def _plant(session: Session, video_id, t_s: float, embedding: list[float]) -> None:
    session.add(VisualFrame(video_id=video_id, t_s=t_s, embedding=embedding))
    session.commit()


def _override(brain: FakeBrain) -> None:
    app.dependency_overrides[get_brain] = lambda: brain


def _clear_override() -> None:
    app.dependency_overrides.pop(get_brain, None)


def test_upload_does_not_wait_for_siglip(client, tiny_mp4: Path) -> None:
    created = _upload(client, tiny_mp4).json()
    assert created["status"] == "ready"
    assert created["visual_status"] == IndexStatus.processing.value
    detail = client.get(f"/videos/{created['id']}").json()
    assert detail["visual_status"] == IndexStatus.ready.value


def test_red_light_surfaces_a_time(client, tiny_mp4: Path) -> None:
    from app.db import get_engine

    video_id = _upload(client, tiny_mp4).json()["id"]
    target = _axis(0)
    other = _axis(1)
    query = "red light"
    engine = get_engine()
    with Session(engine) as session:
        video = session.get(Video, video_id)
        assert video is not None
        _plant(session, video.id, 5.0, target)
        _plant(session, video.id, 1.0, other)
        hits = search_visual(
            session, video.id, query, FakeVisualEmbedder(query_vectors={query: target})
        )
    assert hits
    assert abs(hits[0].t - 5.0) < 0.01


def test_bird_surfaces_a_time(client, tiny_mp4: Path) -> None:
    from app.db import get_engine

    video_id = _upload(client, tiny_mp4).json()["id"]
    bird = _axis(3)
    query = "bird"
    engine = get_engine()
    with Session(engine) as session:
        video = session.get(Video, video_id)
        assert video is not None
        _plant(session, video.id, 12.0, bird)
        hits = search_visual(
            session, video.id, query, FakeVisualEmbedder(query_vectors={query: bird})
        )
    assert hits
    assert abs(hits[0].t - 12.0) < 0.01


def test_second_question_does_not_run_siglip(
    client, tiny_mp4: Path, monkeypatch
) -> None:
    calls: list[int] = []

    def counting(jpegs, model_name: str = ""):
        calls.append(len(jpegs))
        return [[0.0] * VISUAL_DIM for _ in jpegs]

    monkeypatch.setattr("app.ingest.siglip.embed_jpegs", counting)
    video_id = _upload(client, tiny_mp4).json()["id"]
    assert len(calls) == 1
    brain = FakeBrain(
        [
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
            f"/videos/{video_id}/chat", json={"message": "where is the bird?"}
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


def test_look_works_while_visual_processing(
    client, tiny_mp4: Path, monkeypatch
) -> None:
    monkeypatch.setattr("app.ingest.visual.ingest_visual", lambda *_a, **_k: None)
    created = _upload(client, tiny_mp4).json()
    assert created["status"] == "ready"
    assert created["visual_status"] == IndexStatus.processing.value
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


def test_search_visual_does_not_dump_all_times(client, tiny_mp4: Path) -> None:
    from app.db import get_engine

    video_id = _upload(client, tiny_mp4).json()["id"]
    engine = get_engine()
    with Session(engine) as session:
        video = session.get(Video, video_id)
        assert video is not None
        for i in range(20):
            vec = _axis(0 if i < 12 else 5)
            _plant(session, video.id, float(i), vec)
    brain = FakeBrain(
        [
            {
                "do": "search_visual",
                "start_s": None,
                "end_s": None,
                "fps": None,
                "query": "red light",
                "answer": None,
                "times": [],
            },
            {
                "do": "answer",
                "start_s": None,
                "end_s": None,
                "fps": None,
                "query": None,
                "answer": "A red light around those times.",
                "times": [0.0],
            },
        ]
    )
    _override(brain)
    try:
        response = client.post(
            f"/videos/{video_id}/chat", json={"message": "where is the red light?"}
        )
    finally:
        _clear_override()
    assert response.status_code == 200, response.text
    observe = brain.calls[1][-1]["content"]
    assert "not the whole file" in observe
    assert len(re.findall(r"\[\d+\.\d+s\]", observe)) <= TOP_HITS


def test_ingest_does_not_use_capped_get_frames(
    client, tiny_mp4: Path, monkeypatch
) -> None:
    def boom(*_args, **_kwargs):
        raise AssertionError("ingest must not use get_frames")

    monkeypatch.setattr("app.tools.frames.get_frames", boom)
    created = _upload(client, tiny_mp4).json()
    assert client.get(f"/videos/{created['id']}").json()["visual_status"] == "ready"


def test_index_jpegs_deleted_after_ingest(client, tiny_mp4: Path, data_dir: Path) -> None:
    created = _upload(client, tiny_mp4).json()
    folder = video_folder(data_dir, created["id"])
    assert not (folder / "ingest_frames").exists()
    leftover = list(folder.glob("*.jpg"))
    assert leftover == []


def test_audio_only_skips_visual(client, tiny_audio: Path) -> None:
    created = _upload(client, tiny_audio).json()
    assert created["status"] == "ready"
    assert created["has_video"] is False
    assert created["visual_status"] == IndexStatus.skipped.value


def test_probe_error_skips_visual(client) -> None:
    created = client.post(
        "/videos",
        files={"file": ("junk.mp4", b"not a media file" * 32, "video/mp4")},
    ).json()
    assert created["status"] == "error"
    assert created["visual_status"] == IndexStatus.skipped.value


def test_internal_visual_callback(client, tiny_mp4: Path, monkeypatch) -> None:
    from app.db import get_engine

    monkeypatch.setattr("app.ingest.visual.ingest_visual", lambda *_a, **_k: None)
    video_id = _upload(client, tiny_mp4).json()["id"]
    denied = client.post(
        f"/internal/videos/{video_id}/visual",
        json={"status": "ready", "frames": [{"t_s": 3.0, "embedding": _axis(0)}]},
    )
    assert denied.status_code == 403
    accepted = client.post(
        f"/internal/videos/{video_id}/visual",
        headers={"Authorization": f"Bearer {INGEST_SECRET}"},
        json={"status": "ready", "frames": [{"t_s": 3.0, "embedding": _axis(0)}]},
    )
    assert accepted.status_code == 200, accepted.text
    engine = get_engine()
    with Session(engine) as session:
        video = session.get(Video, video_id)
        assert video is not None
        assert video.visual_status == IndexStatus.ready.value
        rows = session.exec(
            select(VisualFrame).where(VisualFrame.video_id == video.id)
        ).all()
        assert len(rows) == 1
        assert abs(rows[0].t_s - 3.0) < 0.01
    ignored = client.post(
        f"/internal/videos/{video_id}/visual",
        headers={"Authorization": f"Bearer {INGEST_SECRET}"},
        json={"status": "ready", "frames": [{"t_s": 9.0, "embedding": _axis(1)}]},
    )
    assert ignored.json().get("ignored") is True
    with Session(engine) as session:
        still = session.exec(
            select(VisualFrame).where(VisualFrame.video_id == video_id)
        ).all()
        assert len(still) == 1


def test_delete_video_removes_visual_frames(client, tiny_mp4: Path) -> None:
    from app.db import get_engine

    video_id = _upload(client, tiny_mp4).json()["id"]
    engine = get_engine()
    with Session(engine) as session:
        video = session.get(Video, video_id)
        assert video is not None
        _plant(session, video.id, 1.0, _axis(0))
    assert client.delete(f"/videos/{video_id}").status_code == 204
    with Session(engine) as session:
        leftover = session.exec(select(VisualFrame)).all()
        assert leftover == []


def test_parse_action_accepts_search_visual() -> None:
    action = parse_action(
        '{"do":"search_visual","start_s":null,"end_s":null,"fps":null,'
        '"query":"bird","answer":null,"times":[]}'
    )
    assert action.do == "search_visual"
    assert action.query == "bird"


def test_search_visual_missing_query_uses_user_question(tiny_mp4: Path) -> None:
    from app.search.visual import VisualHit

    seen: list[str] = []

    def search(query: str) -> list[VisualHit]:
        seen.append(query)
        return [VisualHit(t=5.0, score=0.9)]

    brain = FakeBrain(
        [
            {
                "do": "search_visual",
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
                "answer": "A red light at five seconds.",
                "times": [5.0],
            },
        ]
    )
    result = run_loop(
        tiny_mp4,
        "where is the red light?",
        brain,
        search_visual=search,
        visual_status=IndexStatus.ready.value,
        transcript_status=IndexStatus.ready.value,
    )
    assert seen == ["where is the red light?"]
    observe = brain.calls[1][-1]["content"]
    assert "5.0" in observe
    assert "score" in observe
    assert result.citations == [5.0]
