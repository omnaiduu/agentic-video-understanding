from __future__ import annotations

import re
from pathlib import Path

import pytest
from app.agent.client import FakeBrain
from app.agent.loop import run_loop
from app.agent.schema import parse_action
from app.ingest.frames import extract_index_frames
from app.ingest.dedup import unique_slides
from app.main import app
from app.models import IndexStatus, SlidePage, Video
from app.routes.chat import get_brain
from app.search.colqwen import SLIDE_DIM, FakeSlideEmbedder
from app.search.slides import TOP_HITS, search_slides
from app.storage import video_folder
from sqlmodel import Session, select


INGEST_SECRET = "test-ingest-secret"


def _run_ffmpeg(args: list[str]) -> None:
    import subprocess

    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", *args],
        check=True,
        capture_output=True,
    )


@pytest.fixture(scope="module")
def deck_mp4(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """3s black then 3s white — six 1 FPS frames, two unique slides."""
    media = tmp_path_factory.mktemp("deck")
    black = media / "black.mp4"
    white = media / "white.mp4"
    path = media / "deck.mp4"
    _run_ffmpeg(
        [
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=64x64:d=3",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(black),
        ]
    )
    _run_ffmpeg(
        [
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=white:s=64x64:d=3",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(white),
        ]
    )
    _run_ffmpeg(
        [
            "-y",
            "-i",
            str(black),
            "-i",
            str(white),
            "-filter_complex",
            "[0:v][1:v]concat=n=2:v=1:a=0",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ]
    )
    return path


def _upload(client, path: Path):
    with path.open("rb") as handle:
        return client.post(
            "/videos",
            files={"file": (path.name, handle, "application/octet-stream")},
        )


def _axis(index: int) -> list[float]:
    vector = [0.0] * SLIDE_DIM
    vector[index] = 1.0
    return vector


def _plant(
    session: Session,
    video_id,
    t_start_s: float,
    embedding: list[list[float]],
    t_end_s: float | None = None,
) -> SlidePage:
    row = SlidePage(
        video_id=video_id,
        t_start_s=t_start_s,
        t_end_s=t_end_s if t_end_s is not None else t_start_s + 1.0,
        embeddings=embedding,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def _override(brain: FakeBrain) -> None:
    app.dependency_overrides[get_brain] = lambda: brain


def _clear_override() -> None:
    app.dependency_overrides.pop(get_brain, None)


def test_upload_does_not_wait_for_colqwen(client, tiny_mp4: Path) -> None:
    created = _upload(client, tiny_mp4).json()
    assert created["status"] == "ready"
    assert created["slides_status"] == IndexStatus.processing.value
    detail = client.get(f"/videos/{created['id']}").json()
    assert detail["slides_status"] == IndexStatus.ready.value


def test_unique_slides_not_every_fps_copy(deck_mp4: Path, tmp_path: Path) -> None:
    frames = extract_index_frames(deck_mp4, tmp_path / "raw")
    assert len(frames) >= 5
    slides = unique_slides(frames)
    assert len(slides) == 2
    assert slides[0].t_start_s == pytest.approx(0.0)
    assert slides[1].t_start_s == pytest.approx(3.0)


def test_ingest_keeps_unique_pages_not_twins(client, deck_mp4: Path) -> None:
    from app.db import get_engine

    video_id = _upload(client, deck_mp4).json()["id"]
    engine = get_engine()
    with Session(engine) as session:
        rows = session.exec(
            select(SlidePage).where(SlidePage.video_id == video_id)
        ).all()
        assert len(rows) == 2


def test_pro_99_surfaces_a_time(client, tiny_mp4: Path) -> None:
    from app.db import get_engine

    video_id = _upload(client, tiny_mp4).json()["id"]
    target = [_axis(0)]
    other = [_axis(1)]
    query = "Pro $99"
    engine = get_engine()
    with Session(engine) as session:
        video = session.get(Video, video_id)
        assert video is not None
        _plant(session, video.id, 12.04, target)
        _plant(session, video.id, 1.0, other)
        hits = search_slides(
            session,
            video.id,
            query,
            FakeSlideEmbedder(query_vectors={query: target}),
        )
    assert hits
    assert abs(hits[0].t - 12.04) < 0.01


def test_second_question_does_not_run_colqwen(
    client, tiny_mp4: Path, monkeypatch
) -> None:
    calls: list[int] = []

    def counting(jpegs, model_name: str = ""):
        calls.append(len(jpegs))
        return [[[0.0] * SLIDE_DIM] for _ in jpegs]

    monkeypatch.setattr("app.ingest.colqwen.embed_jpegs", counting)
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
            f"/videos/{video_id}/chat",
            json={"message": "which slide had Pro $99?"},
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


def test_look_works_while_slides_processing(
    client, tiny_mp4: Path, monkeypatch
) -> None:
    monkeypatch.setattr("app.ingest.slides.ingest_slides", lambda *_a, **_k: None)
    created = _upload(client, tiny_mp4).json()
    assert created["status"] == "ready"
    assert created["slides_status"] == IndexStatus.processing.value
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
            json={"message": "what is on screen at 0:10?"},
        )
    finally:
        _clear_override()
    assert response.status_code == 200, response.text
    assert response.json()["steps"][0]["do"] == "look"
    assert response.json()["steps"][0]["ok"] is True


def test_search_slides_then_look_reads_the_frame(client, tiny_mp4: Path) -> None:
    from app.db import get_engine

    video_id = _upload(client, tiny_mp4).json()["id"]
    engine = get_engine()
    with Session(engine) as session:
        video = session.get(Video, video_id)
        assert video is not None
        _plant(session, video.id, 12.04, [_axis(0)])
    brain = FakeBrain(
        [
            {
                "do": "search_slides",
                "start_s": None,
                "end_s": None,
                "fps": None,
                "query": "Pro $99",
                "answer": None,
                "times": [],
            },
            {
                "do": "look",
                "start_s": 12.04,
                "end_s": 12.08,
                "fps": 4,
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
                "answer": "The slide shows Pro $99.",
                "times": [12.04],
            },
        ]
    )
    _override(brain)
    try:
        response = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "which slide had Pro $99?"},
        )
    finally:
        _clear_override()
    # 12.04 is past the 1s fixture; look is refused, Gemma still answers from the hit.
    assert response.status_code == 200, response.text
    body = response.json()
    assert [step["do"] for step in body["steps"]][0] == "search_slides"
    assert body["answer"] == "The slide shows Pro $99."
    observe = brain.calls[1][-1]["content"]
    assert "12.0" in observe
    assert "look at a hit to read the real frame" in observe


def test_search_slides_does_not_dump_all_times(client, tiny_mp4: Path) -> None:
    from app.db import get_engine

    video_id = _upload(client, tiny_mp4).json()["id"]
    engine = get_engine()
    with Session(engine) as session:
        video = session.get(Video, video_id)
        assert video is not None
        for i in range(20):
            vec = [_axis(0 if i < 12 else 5)]
            _plant(session, video.id, float(i), vec)
    brain = FakeBrain(
        [
            {
                "do": "search_slides",
                "start_s": None,
                "end_s": None,
                "fps": None,
                "query": "Pro $99",
                "answer": None,
                "times": [],
            },
            {
                "do": "answer",
                "start_s": None,
                "end_s": None,
                "fps": None,
                "query": None,
                "answer": "Around those times.",
                "times": [0.0],
            },
        ]
    )
    _override(brain)
    try:
        response = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "which slide had Pro $99?"},
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
    assert client.get(f"/videos/{created['id']}").json()["slides_status"] == "ready"


def test_index_jpegs_deleted_after_ingest(client, tiny_mp4: Path, data_dir: Path) -> None:
    created = _upload(client, tiny_mp4).json()
    folder = video_folder(data_dir, created["id"])
    assert not (folder / "ingest_slides").exists()
    leftover = list(folder.glob("*.jpg"))
    assert leftover == []


def test_audio_only_skips_slides(client, tiny_audio: Path) -> None:
    created = _upload(client, tiny_audio).json()
    assert created["status"] == "ready"
    assert created["has_video"] is False
    assert created["slides_status"] == IndexStatus.skipped.value


def test_probe_error_skips_slides(client) -> None:
    created = client.post(
        "/videos",
        files={"file": ("junk.mp4", b"not a media file" * 32, "video/mp4")},
    ).json()
    assert created["status"] == "error"
    assert created["slides_status"] == IndexStatus.skipped.value


def test_internal_slides_callback(client, tiny_mp4: Path, monkeypatch) -> None:
    from app.db import get_engine

    monkeypatch.setattr("app.ingest.slides.ingest_slides", lambda *_a, **_k: None)
    video_id = _upload(client, tiny_mp4).json()["id"]
    denied = client.post(
        f"/internal/videos/{video_id}/slide-pages",
        json={
            "status": "ready",
            "slides": [
                {
                    "t_start_s": 12.04,
                    "t_end_s": 12.58,
                    "embeddings": [_axis(0)],
                }
            ],
        },
    )
    assert denied.status_code == 403
    accepted = client.post(
        f"/internal/videos/{video_id}/slide-pages",
        headers={"Authorization": f"Bearer {INGEST_SECRET}"},
        json={
            "status": "ready",
            "slides": [
                {
                    "t_start_s": 12.04,
                    "t_end_s": 12.58,
                    "embeddings": [_axis(0)],
                }
            ],
        },
    )
    assert accepted.status_code == 200, accepted.text
    engine = get_engine()
    with Session(engine) as session:
        video = session.get(Video, video_id)
        assert video is not None
        assert video.slides_status == IndexStatus.ready.value
        rows = session.exec(
            select(SlidePage).where(SlidePage.video_id == video.id)
        ).all()
        assert len(rows) == 1
        assert abs(rows[0].t_start_s - 12.04) < 0.01
    ignored = client.post(
        f"/internal/videos/{video_id}/slide-pages",
        headers={"Authorization": f"Bearer {INGEST_SECRET}"},
        json={
            "status": "ready",
            "slides": [
                {
                    "t_start_s": 9.0,
                    "t_end_s": 10.0,
                    "embeddings": [_axis(1)],
                }
            ],
        },
    )
    assert ignored.json().get("ignored") is True
    with Session(engine) as session:
        still = session.exec(
            select(SlidePage).where(SlidePage.video_id == video_id)
        ).all()
        assert len(still) == 1


def test_delete_video_removes_slide_pages(client, tiny_mp4: Path) -> None:
    from app.db import get_engine

    video_id = _upload(client, tiny_mp4).json()["id"]
    engine = get_engine()
    with Session(engine) as session:
        video = session.get(Video, video_id)
        assert video is not None
        _plant(session, video.id, 1.0, [_axis(0)])
    assert client.delete(f"/videos/{video_id}").status_code == 204
    with Session(engine) as session:
        leftover = session.exec(select(SlidePage)).all()
        assert leftover == []


def test_parse_action_accepts_search_slides() -> None:
    action = parse_action(
        '{"do":"search_slides","start_s":null,"end_s":null,"fps":null,'
        '"query":"Pro $99","answer":null,"times":[]}'
    )
    assert action.do == "search_slides"
    assert action.query == "Pro $99"


def test_search_slides_missing_query_uses_user_question(tiny_mp4: Path) -> None:
    from app.search.slides import SlideHit
    import uuid

    seen: list[str] = []

    def search(query: str) -> list[SlideHit]:
        seen.append(query)
        return [
            SlideHit(
                t=12.04,
                t_end=12.58,
                score=0.9,
                slide_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            )
        ]

    brain = FakeBrain(
        [
            {
                "do": "search_slides",
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
                "answer": "Pro $99 is on that slide.",
                "times": [12.04],
            },
        ]
    )
    result = run_loop(
        tiny_mp4,
        "which slide had Pro $99?",
        brain,
        search_slides=search,
        slides_status=IndexStatus.ready.value,
        transcript_status=IndexStatus.ready.value,
        visual_status=IndexStatus.ready.value,
    )
    assert seen == ["which slide had Pro $99?"]
    observe = brain.calls[1][-1]["content"]
    assert "12.0" in observe
    assert "score" in observe
    assert "slide_id" in observe
    assert result.citations == [12.04]


def test_legacy_pending_slides_skipped_on_get(client, tiny_mp4: Path) -> None:
    from app.db import get_engine

    created = _upload(client, tiny_mp4).json()
    video_id = created["id"]
    engine = get_engine()
    with Session(engine) as session:
        video = session.get(Video, video_id)
        assert video is not None
        video.slides_status = IndexStatus.pending.value
        session.add(video)
        session.commit()

    detail = client.get(f"/videos/{video_id}").json()
    assert detail["slides_status"] == IndexStatus.skipped.value
    listed = client.get("/videos").json()
    match = next(row for row in listed if row["id"] == video_id)
    assert match["slides_status"] == IndexStatus.skipped.value

    with Session(engine) as session:
        video = session.get(Video, video_id)
        assert video is not None
        assert video.slides_status == IndexStatus.skipped.value
        video.transcript_status = IndexStatus.processing.value
        video.slides_status = IndexStatus.pending.value
        session.add(video)
        session.commit()

    waiting = client.get(f"/videos/{video_id}").json()
    assert waiting["slides_status"] == IndexStatus.pending.value

    with Session(engine) as session:
        video = session.get(Video, video_id)
        assert video is not None
        video.transcript_status = IndexStatus.ready.value
        video.slides_status = IndexStatus.processing.value
        session.add(video)
        session.commit()

    still = client.get(f"/videos/{video_id}").json()
    assert still["slides_status"] == IndexStatus.processing.value


def test_search_visual_still_exists(client, tiny_mp4: Path) -> None:
    created = _upload(client, tiny_mp4).json()
    detail = client.get(f"/videos/{created['id']}").json()
    assert detail["visual_status"] == IndexStatus.ready.value
    assert detail["slides_status"] == IndexStatus.ready.value
    action = parse_action(
        '{"do":"search_visual","start_s":null,"end_s":null,"fps":null,'
        '"query":"bird","answer":null,"times":[]}'
    )
    assert action.do == "search_visual"
