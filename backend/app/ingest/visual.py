"""Background picture ingest: 1 FPS JPEGs, SigLIP, write VisualFrame, delete JPEGs."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import BackgroundTasks
from sqlalchemy import text
from sqlmodel import Session

from app.db import get_engine
from app.ingest.audio import IngestError
from app.ingest.frames import (
    extract_index_frames,
    frames_tar_path,
    ingest_frames_dir,
    pack_index_frames,
)
from app.ingest import siglip as siglip_mod
from app.models import IndexStatus, Video, VideoStatus, VisualFrame
from app.search.siglip import VISUAL_DIM
from app.settings import Settings, get_settings
from app.storage import video_folder


def _folder(settings: Settings, video_id: uuid.UUID) -> Path:
    return video_folder(settings.data_dir, video_id)


def cleanup_index_jpegs(folder: Path) -> None:
    dest = ingest_frames_dir(folder)
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    tar = frames_tar_path(folder)
    tar.unlink(missing_ok=True)


def save_visual_frames(
    session: Session,
    video: Video,
    times: list[float],
    embeddings: list[list[float]],
) -> None:
    session.execute(
        text("DELETE FROM visual_frames WHERE video_id = :vid"),
        {"vid": video.id},
    )
    for t_s, vector in zip(times, embeddings):
        if len(vector) != VISUAL_DIM:
            raise ValueError(f"visual embedding must have {VISUAL_DIM} dimensions")
        session.add(
            VisualFrame(video_id=video.id, t_s=t_s, embedding=vector)
        )
    video.visual_status = IndexStatus.ready.value
    session.add(video)
    session.commit()


def _mark_error(session: Session, video: Video) -> None:
    video.visual_status = IndexStatus.error.value
    session.add(video)
    session.commit()


def ingest_visual(video_id: uuid.UUID) -> None:
    settings = get_settings()
    engine = get_engine()
    folder = _folder(settings, video_id)
    with Session(engine) as session:
        video = session.get(Video, video_id)
        if video is None:
            return
        if video.visual_status == IndexStatus.ready.value:
            return
        if video.visual_status != IndexStatus.processing.value:
            return
        if video.status != VideoStatus.ready.value or not video.has_video:
            video.visual_status = IndexStatus.skipped.value
            session.add(video)
            session.commit()
            return
        dest = ingest_frames_dir(folder)
        try:
            frames = extract_index_frames(video.path, dest)
            vectors = siglip_mod.embed_jpegs(
                [frame.jpeg for frame in frames], settings.siglip_model
            )
            save_visual_frames(
                session,
                video,
                [frame.t_s for frame in frames],
                vectors,
            )
        except Exception:
            session.rollback()
            video = session.get(Video, video_id)
            if video is not None:
                _mark_error(session, video)
        finally:
            cleanup_index_jpegs(folder)


def spawn_modal_visual(video_id: uuid.UUID) -> None:
    settings = get_settings()
    engine = get_engine()
    folder = _folder(settings, video_id)
    with Session(engine) as session:
        video = session.get(Video, video_id)
        if video is None:
            return
        if video.visual_status == IndexStatus.ready.value:
            return
        if not settings.public_base_url or not settings.ingest_secret:
            _mark_error(session, video)
            return
        dest = ingest_frames_dir(folder)
        try:
            extract_index_frames(video.path, dest)
            pack_index_frames(dest, frames_tar_path(folder))
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
        except IngestError:
            _mark_error(session, video)
            cleanup_index_jpegs(folder)
            return
        base = settings.public_base_url.rstrip("/")
        try:
            import modal

            embed = modal.Function.from_name(
                settings.modal_ingest_app, "embed_visual"
            )
            embed.spawn(
                str(video.id),
                f"{base}/internal/videos/{video.id}/frames",
                f"{base}/internal/videos/{video.id}/visual",
                settings.ingest_secret,
                settings.siglip_model,
            )
        except Exception:
            _mark_error(session, video)
            cleanup_index_jpegs(folder)


def schedule_visual(
    session: Session,
    video: Video,
    background_tasks: BackgroundTasks,
    settings: Settings | None = None,
) -> None:
    """Set visual_status and queue work. POST /videos must not wait for SigLIP."""
    cfg = settings or get_settings()
    if video.visual_status in (
        IndexStatus.ready.value,
        IndexStatus.processing.value,
    ):
        return
    if video.status != VideoStatus.ready.value or not video.has_video:
        video.visual_status = IndexStatus.skipped.value
        session.add(video)
        session.commit()
        return
    video.visual_status = IndexStatus.processing.value
    session.add(video)
    session.commit()
    if cfg.ingest == "modal":
        background_tasks.add_task(spawn_modal_visual, video.id)
        return
    background_tasks.add_task(ingest_visual, video.id)
