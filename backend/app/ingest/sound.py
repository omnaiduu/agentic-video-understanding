"""Background sound ingest: 3s chunks, CLAP, write AudioChunk, delete wavs."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import BackgroundTasks
from sqlalchemy import text
from sqlmodel import Session

from app.db import get_engine
from app.ingest.audio import IngestError
from app.ingest.chunks import (
    clap_wav_path,
    chunks_tar_path,
    extract_clap_audio,
    ingest_chunks_dir,
    pack_index_chunks,
    slice_index_chunks,
    wav_is_mute,
)
from app.ingest import clap as clap_mod
from app.models import AudioChunk, IndexStatus, Video, VideoStatus
from app.search.clap import AUDIO_DIM
from app.settings import Settings, get_settings
from app.storage import video_folder


def _folder(settings: Settings, video_id: uuid.UUID) -> Path:
    return video_folder(settings.data_dir, video_id)


def cleanup_index_chunks(folder: Path) -> None:
    dest = ingest_chunks_dir(folder)
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    tar = chunks_tar_path(folder)
    tar.unlink(missing_ok=True)
    clap_wav_path(folder).unlink(missing_ok=True)


def save_audio_chunks(
    session: Session,
    video: Video,
    starts: list[float],
    ends: list[float],
    embeddings: list[list[float]],
) -> None:
    session.execute(
        text("DELETE FROM audio_chunks WHERE video_id = :vid"),
        {"vid": video.id},
    )
    for start_s, end_s, vector in zip(starts, ends, embeddings):
        if len(vector) != AUDIO_DIM:
            raise ValueError(f"audio embedding must have {AUDIO_DIM} dimensions")
        session.add(
            AudioChunk(
                video_id=video.id,
                start_s=start_s,
                end_s=end_s,
                embedding=vector,
            )
        )
    video.audio_status = IndexStatus.ready.value
    session.add(video)
    session.commit()


def _mark_error(session: Session, video: Video) -> None:
    video.audio_status = IndexStatus.error.value
    session.add(video)
    session.commit()


def _mark_skipped(session: Session, video: Video) -> None:
    video.audio_status = IndexStatus.skipped.value
    session.add(video)
    session.commit()


def ingest_sound(video_id: uuid.UUID) -> None:
    settings = get_settings()
    engine = get_engine()
    folder = _folder(settings, video_id)
    with Session(engine) as session:
        video = session.get(Video, video_id)
        if video is None:
            return
        if video.audio_status == IndexStatus.ready.value:
            return
        if video.audio_status != IndexStatus.processing.value:
            return
        if video.status != VideoStatus.ready.value or not video.has_audio:
            _mark_skipped(session, video)
            return
        wav = clap_wav_path(folder)
        dest = ingest_chunks_dir(folder)
        try:
            extract_clap_audio(video.path, wav)
            if wav_is_mute(wav):
                _mark_skipped(session, video)
                return
            chunks = slice_index_chunks(wav, dest)
            vectors = clap_mod.embed_wavs(
                [chunk.wav for chunk in chunks], settings.clap_model
            )
            save_audio_chunks(
                session,
                video,
                [chunk.start_s for chunk in chunks],
                [chunk.end_s for chunk in chunks],
                vectors,
            )
        except Exception:
            session.rollback()
            video = session.get(Video, video_id)
            if video is not None:
                _mark_error(session, video)
        finally:
            cleanup_index_chunks(folder)


def spawn_modal_sound(video_id: uuid.UUID) -> None:
    settings = get_settings()
    engine = get_engine()
    folder = _folder(settings, video_id)
    with Session(engine) as session:
        video = session.get(Video, video_id)
        if video is None:
            return
        if video.audio_status == IndexStatus.ready.value:
            return
        if not settings.public_base_url or not settings.ingest_secret:
            _mark_error(session, video)
            return
        wav = clap_wav_path(folder)
        dest = ingest_chunks_dir(folder)
        try:
            extract_clap_audio(video.path, wav)
            if wav_is_mute(wav):
                _mark_skipped(session, video)
                cleanup_index_chunks(folder)
                return
            slice_index_chunks(wav, dest)
            pack_index_chunks(dest, chunks_tar_path(folder))
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            wav.unlink(missing_ok=True)
        except IngestError:
            _mark_error(session, video)
            cleanup_index_chunks(folder)
            return
        base = settings.public_base_url.rstrip("/")
        try:
            import modal

            embed = modal.Function.from_name(
                settings.modal_ingest_app, "embed_audio"
            )
            embed.spawn(
                str(video.id),
                f"{base}/internal/videos/{video.id}/chunks",
                f"{base}/internal/videos/{video.id}/sound",
                settings.ingest_secret,
                settings.clap_model,
            )
        except Exception:
            _mark_error(session, video)
            cleanup_index_chunks(folder)


def schedule_sound(
    session: Session,
    video: Video,
    background_tasks: BackgroundTasks,
    settings: Settings | None = None,
) -> None:
    """Set audio_status and queue work. POST /videos must not wait for CLAP."""
    cfg = settings or get_settings()
    if video.audio_status in (
        IndexStatus.ready.value,
        IndexStatus.processing.value,
    ):
        return
    if video.status != VideoStatus.ready.value or not video.has_audio:
        video.audio_status = IndexStatus.skipped.value
        session.add(video)
        session.commit()
        return
    video.audio_status = IndexStatus.processing.value
    session.add(video)
    session.commit()
    if cfg.ingest == "modal":
        background_tasks.add_task(spawn_modal_sound, video.id)
        return
    background_tasks.add_task(ingest_sound, video.id)
