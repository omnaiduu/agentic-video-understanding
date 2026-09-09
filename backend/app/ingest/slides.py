"""Background slide ingest: unique 1 FPS frames, ColQwen patches, write SlidePage."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import BackgroundTasks
from sqlalchemy import text
from sqlmodel import Session

from app.db import get_engine
from app.ingest.audio import IngestError
from app.ingest import colqwen as colqwen_mod
from app.ingest.dedup import (
    ingest_slides_dir,
    slides_tar_path,
    unique_slides,
    write_unique_slides,
)
from app.ingest.frames import extract_index_frames, pack_index_frames
from app.models import IndexStatus, SlidePage, Video, VideoStatus
from app.search.colqwen import SLIDE_DIM
from app.settings import Settings, get_settings
from app.storage import video_folder


_TERMINAL = {
    IndexStatus.ready.value,
    IndexStatus.skipped.value,
    IndexStatus.error.value,
}


def skip_stale_pending_slides(video: Video) -> bool:
    """0008 left finished videos at slides_status=pending. Skip those leftovers."""
    if video.slides_status != IndexStatus.pending.value:
        return False
    if video.transcript_status not in _TERMINAL:
        return False
    if video.visual_status not in _TERMINAL:
        return False
    if video.audio_status not in _TERMINAL:
        return False
    video.slides_status = IndexStatus.skipped.value
    return True


def _folder(settings: Settings, video_id: uuid.UUID) -> Path:
    return video_folder(settings.data_dir, video_id)


def cleanup_index_slides(folder: Path) -> None:
    dest = ingest_slides_dir(folder)
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    tar = slides_tar_path(folder)
    tar.unlink(missing_ok=True)


def save_slide_pages(
    session: Session,
    video: Video,
    starts: list[float],
    ends: list[float],
    embeddings: list[list[list[float]]],
) -> None:
    session.execute(
        text("DELETE FROM slide_pages WHERE video_id = :vid"),
        {"vid": video.id},
    )
    for start_s, end_s, patches in zip(starts, ends, embeddings):
        if not patches:
            raise ValueError("slide page needs at least one patch vector")
        for vector in patches:
            if len(vector) != SLIDE_DIM:
                raise ValueError(f"slide patch must have {SLIDE_DIM} dimensions")
        session.add(
            SlidePage(
                video_id=video.id,
                t_start_s=start_s,
                t_end_s=end_s,
                embeddings=patches,
            )
        )
    video.slides_status = IndexStatus.ready.value
    session.add(video)
    session.commit()


def _mark_error(session: Session, video: Video) -> None:
    video.slides_status = IndexStatus.error.value
    session.add(video)
    session.commit()


def ingest_slides(video_id: uuid.UUID) -> None:
    settings = get_settings()
    engine = get_engine()
    folder = _folder(settings, video_id)
    with Session(engine) as session:
        video = session.get(Video, video_id)
        if video is None:
            return
        if video.slides_status == IndexStatus.ready.value:
            return
        if video.slides_status != IndexStatus.processing.value:
            return
        if video.status != VideoStatus.ready.value or not video.has_video:
            video.slides_status = IndexStatus.skipped.value
            session.add(video)
            session.commit()
            return
        dest = ingest_slides_dir(folder)
        raw = dest / "raw"
        try:
            frames = extract_index_frames(video.path, raw)
            slides = unique_slides(frames)
            packed = write_unique_slides(slides, dest)
            shutil.rmtree(raw, ignore_errors=True)
            vectors = colqwen_mod.embed_jpegs(
                [slide.jpeg for slide in packed], settings.colqwen_model
            )
            save_slide_pages(
                session,
                video,
                [slide.t_start_s for slide in packed],
                [slide.t_end_s for slide in packed],
                vectors,
            )
        except Exception:
            session.rollback()
            video = session.get(Video, video_id)
            if video is not None:
                _mark_error(session, video)
        finally:
            cleanup_index_slides(folder)


def spawn_modal_slides(video_id: uuid.UUID) -> None:
    settings = get_settings()
    engine = get_engine()
    folder = _folder(settings, video_id)
    with Session(engine) as session:
        video = session.get(Video, video_id)
        if video is None:
            return
        if video.slides_status == IndexStatus.ready.value:
            return
        if not settings.public_base_url or not settings.ingest_secret:
            _mark_error(session, video)
            return
        dest = ingest_slides_dir(folder)
        raw = dest / "raw"
        try:
            frames = extract_index_frames(video.path, raw)
            slides = unique_slides(frames)
            write_unique_slides(slides, dest)
            shutil.rmtree(raw, ignore_errors=True)
            pack_index_frames(dest, slides_tar_path(folder))
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
        except IngestError:
            _mark_error(session, video)
            cleanup_index_slides(folder)
            return
        base = settings.public_base_url.rstrip("/")
        try:
            import modal

            embed = modal.Function.from_name(
                settings.modal_ingest_app, "embed_slides"
            )
            embed.spawn(
                str(video.id),
                f"{base}/internal/videos/{video.id}/slides",
                f"{base}/internal/videos/{video.id}/slide-pages",
                settings.ingest_secret,
                settings.colqwen_model,
            )
        except Exception:
            _mark_error(session, video)
            cleanup_index_slides(folder)


def schedule_slides(
    session: Session,
    video: Video,
    background_tasks: BackgroundTasks,
    settings: Settings | None = None,
) -> None:
    """Set slides_status and queue work. POST /videos must not wait for ColQwen."""
    cfg = settings or get_settings()
    if video.slides_status in (
        IndexStatus.ready.value,
        IndexStatus.processing.value,
    ):
        return
    if video.status != VideoStatus.ready.value or not video.has_video:
        video.slides_status = IndexStatus.skipped.value
        session.add(video)
        session.commit()
        return
    video.slides_status = IndexStatus.processing.value
    session.add(video)
    session.commit()
    if cfg.ingest == "modal":
        background_tasks.add_task(spawn_modal_slides, video.id)
        return
    background_tasks.add_task(ingest_slides, video.id)
