"""Background speech ingest: extract full audio, Whisper, embed, write lines."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import BackgroundTasks
from sqlalchemy import text
from sqlmodel import Session

from app.db import get_engine
from app.ingest.audio import IngestError, extract_full_audio
from app.ingest import whisper as whisper_mod
from app.ingest.whisper import TranscriptSegment
from app.models import IndexStatus, TranscriptLine, Video, VideoStatus
from app.search.embed import Embedder, build_embedder
from app.settings import Settings, get_settings
from app.storage import video_folder


def full_wav_path(data_dir: Path, video_id: uuid.UUID) -> Path:
    return video_folder(data_dir, video_id) / "full.wav"


def save_segments(
    session: Session,
    video: Video,
    segments: list[TranscriptSegment],
    embedder: Embedder,
    embeddings: list[list[float] | None] | None = None,
) -> None:
    session.execute(
        text("DELETE FROM transcript_lines WHERE video_id = :vid"),
        {"vid": video.id},
    )
    texts = [segment.text.strip() for segment in segments]
    needed = [
        i
        for i, segment in enumerate(segments)
        if segment.text.strip()
        and (embeddings is None or embeddings[i] is None)
    ]
    computed: dict[int, list[float]] = {}
    if needed:
        vectors = embedder.embed_passages([texts[i] for i in needed])
        for index, vector in zip(needed, vectors):
            computed[index] = vector
    for i, segment in enumerate(segments):
        line_text = segment.text.strip()
        if not line_text:
            continue
        vector = None
        if embeddings is not None:
            vector = embeddings[i]
        if vector is None:
            vector = computed.get(i)
        session.add(
            TranscriptLine(
                video_id=video.id,
                start_s=segment.start_s,
                end_s=segment.end_s,
                text=line_text,
                embedding=vector,
            )
        )
    video.transcript_status = IndexStatus.ready.value
    session.add(video)
    session.commit()


def _mark_error(session: Session, video: Video) -> None:
    video.transcript_status = IndexStatus.error.value
    session.add(video)
    session.commit()


def ingest_video(video_id: uuid.UUID) -> None:
    """Run on the laptop (fake) or after Modal posts segments. Opens its own session."""
    settings = get_settings()
    engine = get_engine()
    with Session(engine) as session:
        video = session.get(Video, video_id)
        if video is None:
            return
        if video.transcript_status == IndexStatus.ready.value:
            return
        if video.transcript_status != IndexStatus.processing.value:
            return
        if video.status != VideoStatus.ready.value or not video.has_audio:
            video.transcript_status = IndexStatus.skipped.value
            session.add(video)
            session.commit()
            return
        wav = full_wav_path(settings.data_dir, video.id)
        try:
            extract_full_audio(video.path, wav)
            segments = whisper_mod.transcribe_wav(wav, settings.whisper_model)
            save_segments(session, video, segments, build_embedder(settings))
        except Exception:
            session.rollback()
            video = session.get(Video, video_id)
            if video is not None:
                _mark_error(session, video)
        finally:
            if settings.ingest == "fake" and wav.exists():
                wav.unlink(missing_ok=True)


def spawn_modal_ingest(video_id: uuid.UUID) -> None:
    settings = get_settings()
    engine = get_engine()
    with Session(engine) as session:
        video = session.get(Video, video_id)
        if video is None:
            return
        if video.transcript_status == IndexStatus.ready.value:
            return
        if not settings.public_base_url or not settings.ingest_secret:
            _mark_error(session, video)
            return
        wav = full_wav_path(settings.data_dir, video.id)
        try:
            extract_full_audio(video.path, wav)
        except IngestError:
            _mark_error(session, video)
            return
        base = settings.public_base_url.rstrip("/")
        try:
            import modal

            transcribe = modal.Function.from_name(
                settings.modal_ingest_app, "transcribe_video"
            )
            transcribe.spawn(
                str(video.id),
                f"{base}/internal/videos/{video.id}/audio",
                f"{base}/internal/videos/{video.id}/transcript",
                settings.ingest_secret,
                settings.whisper_model,
                settings.embed_model,
            )
        except Exception:
            _mark_error(session, video)


def schedule_transcript(
    session: Session,
    video: Video,
    background_tasks: BackgroundTasks,
    settings: Settings | None = None,
) -> None:
    """Set transcript_status and queue work. POST /videos must not wait for Whisper."""
    cfg = settings or get_settings()
    if video.transcript_status in (
        IndexStatus.ready.value,
        IndexStatus.processing.value,
    ):
        return
    if video.status != VideoStatus.ready.value or not video.has_audio:
        video.transcript_status = IndexStatus.skipped.value
        session.add(video)
        session.commit()
        return
    video.transcript_status = IndexStatus.processing.value
    session.add(video)
    session.commit()
    if cfg.ingest == "modal":
        background_tasks.add_task(spawn_modal_ingest, video.id)
        return
    background_tasks.add_task(ingest_video, video.id)
