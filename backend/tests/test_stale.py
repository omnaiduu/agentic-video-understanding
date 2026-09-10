from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlmodel import Session

from app.db import get_engine
from app.ingest.stale import STALE_PROCESSING_S, fail_stale_processing_indexes
from app.models import IndexStatus, Video, VideoStatus


def _upload(client, path):
    with path.open("rb") as handle:
        return client.post(
            "/videos",
            files={"file": (path.name, handle, "application/octet-stream")},
        )


def test_fail_stale_processing_indexes_unit() -> None:
    now = datetime.now(timezone.utc)
    video = Video(
        original_filename="talk.mp4",
        path="/tmp/talk.mp4",
        status=VideoStatus.ready.value,
        transcript_status=IndexStatus.processing.value,
        visual_status=IndexStatus.error.value,
        audio_status=IndexStatus.error.value,
        slides_status=IndexStatus.ready.value,
        created_at=now - timedelta(seconds=STALE_PROCESSING_S + 10),
    )
    assert fail_stale_processing_indexes(video, now=now) is True
    assert video.transcript_status == IndexStatus.error.value
    assert video.visual_status == IndexStatus.error.value
    assert video.slides_status == IndexStatus.ready.value


def test_fresh_processing_stays_processing() -> None:
    now = datetime.now(timezone.utc)
    video = Video(
        original_filename="talk.mp4",
        path="/tmp/talk.mp4",
        status=VideoStatus.ready.value,
        transcript_status=IndexStatus.processing.value,
        created_at=now,
    )
    assert fail_stale_processing_indexes(video, now=now) is False
    assert video.transcript_status == IndexStatus.processing.value


def test_get_video_marks_stale_processing_error(
    client, tiny_mp4, monkeypatch
) -> None:
    monkeypatch.setattr("app.ingest.speech.ingest_video", lambda *_a, **_k: None)
    monkeypatch.setattr("app.ingest.visual.ingest_visual", lambda *_a, **_k: None)
    monkeypatch.setattr("app.ingest.sound.ingest_sound", lambda *_a, **_k: None)
    monkeypatch.setattr("app.ingest.slides.ingest_slides", lambda *_a, **_k: None)
    video_id = _upload(client, tiny_mp4).json()["id"]
    fresh = client.get(f"/videos/{video_id}").json()
    assert fresh["transcript_status"] == IndexStatus.processing.value
    engine = get_engine()
    with Session(engine) as session:
        video = session.get(Video, video_id)
        assert video is not None
        video.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
        session.add(video)
        session.commit()
    body = client.get(f"/videos/{video_id}").json()
    assert body["transcript_status"] == IndexStatus.error.value
    assert body["visual_status"] == IndexStatus.error.value
    assert body["audio_status"] == IndexStatus.error.value
    assert body["slides_status"] == IndexStatus.error.value


def test_stale_processing_lets_pending_slides_skip(
    client, tiny_mp4, monkeypatch
) -> None:
    monkeypatch.setattr("app.ingest.speech.ingest_video", lambda *_a, **_k: None)
    monkeypatch.setattr("app.ingest.visual.ingest_visual", lambda *_a, **_k: None)
    monkeypatch.setattr("app.ingest.sound.ingest_sound", lambda *_a, **_k: None)
    monkeypatch.setattr("app.ingest.slides.ingest_slides", lambda *_a, **_k: None)
    video_id = _upload(client, tiny_mp4).json()["id"]
    engine = get_engine()
    with Session(engine) as session:
        video = session.get(Video, video_id)
        assert video is not None
        video.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
        video.slides_status = IndexStatus.pending.value
        session.add(video)
        session.commit()
    body = client.get(f"/videos/{video_id}").json()
    assert body["transcript_status"] == IndexStatus.error.value
    assert body["slides_status"] == IndexStatus.skipped.value
