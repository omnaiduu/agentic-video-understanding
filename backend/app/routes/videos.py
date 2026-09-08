from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlmodel import Session, select
from starlette.datastructures import UploadFile

from app.db import get_session
from app.ingest.speech import schedule_transcript
from app.ingest.visual import schedule_visual
from app.media.probe import ProbeError, probe
from app.models import IndexStatus, Video, VideoOut, VideoStatus
from app.settings import Settings, get_settings
from app.storage import (
    OversizeError,
    copy_file,
    original_dest,
    remove_folder,
    safe_filename,
    save_upload,
    video_folder,
)

router = APIRouter()


class PathIn(BaseModel):
    path: str


def _to_out(video: Video) -> VideoOut:
    return VideoOut.model_validate(video, from_attributes=True)


def _guess_kind(filename: str) -> str:
    return "video" if Path(filename).suffix.lower() == ".mp4" else "audio"


def _apply_probe(video: Video, dest: Path) -> None:
    try:
        result = probe(dest)
    except ProbeError as exc:
        video.status = VideoStatus.error.value
        video.transcript_status = IndexStatus.skipped.value
        video.visual_status = IndexStatus.skipped.value
        video.error_message = str(exc)[:2000]
        if not video.kind:
            video.kind = _guess_kind(video.original_filename)
        return
    video.kind = result.kind
    video.duration_s = result.duration_s
    video.fps = result.fps
    video.has_audio = result.has_audio
    video.has_video = result.has_video
    video.status = VideoStatus.ready.value
    video.error_message = None


def _insert(session: Session, video: Video) -> Video:
    session.add(video)
    session.commit()
    session.refresh(video)
    _apply_probe(video, Path(video.path))
    session.add(video)
    session.commit()
    session.refresh(video)
    return video


def _resolve_source(raw: str) -> Path:
    if "\x00" in raw:
        raise HTTPException(status_code=400, detail="invalid path")
    candidate = Path(raw).expanduser()
    if ".." in candidate.parts:
        raise HTTPException(status_code=400, detail="path must not contain '..'")
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail="path is not a file") from exc
    if not resolved.is_file():
        raise HTTPException(status_code=400, detail="path is not a file")
    return resolved


@router.post("/videos", response_model=VideoOut, status_code=201)
async def create_video(
    request: Request,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> VideoOut:
    content_type = (request.headers.get("content-type") or "").lower()
    video_id = uuid.uuid4()
    folder = video_folder(settings.data_dir, video_id)

    if "application/json" in content_type:
        try:
            payload = PathIn.model_validate(await request.json())
        except Exception as exc:
            raise HTTPException(status_code=400, detail="path is required") from exc
        source = _resolve_source(payload.path)
        filename = safe_filename(source.name)
        dest = original_dest(folder, filename)
        try:
            copy_file(source, dest, settings.max_upload_bytes)
        except OversizeError as exc:
            raise HTTPException(status_code=413, detail="file too large") from exc
        video = Video(
            id=video_id,
            original_filename=filename,
            path=str(dest),
            kind=_guess_kind(filename),
            status=VideoStatus.uploaded.value,
            transcript_status=IndexStatus.pending.value,
            visual_status=IndexStatus.pending.value,
        )
        video = _insert(session, video)
        schedule_transcript(session, video, background_tasks, settings)
        schedule_visual(session, video, background_tasks, settings)
        session.refresh(video)
        return _to_out(video)

    if "multipart/form-data" not in content_type:
        raise HTTPException(status_code=400, detail="send a multipart file or JSON path")

    form = await request.form(max_part_size=settings.max_upload_bytes)
    upload = form.get("file")
    if not isinstance(upload, UploadFile):
        raise HTTPException(status_code=400, detail="file is required")

    filename = safe_filename(upload.filename)
    dest = original_dest(folder, filename)
    try:
        await save_upload(upload, dest, settings.max_upload_bytes)
    except OversizeError as exc:
        raise HTTPException(status_code=413, detail="file too large") from exc
    finally:
        await upload.close()

    video = Video(
        id=video_id,
        original_filename=filename,
        path=str(dest),
        kind=_guess_kind(filename),
        status=VideoStatus.uploaded.value,
        transcript_status=IndexStatus.pending.value,
        visual_status=IndexStatus.pending.value,
    )
    video = _insert(session, video)
    schedule_transcript(session, video, background_tasks, settings)
    schedule_visual(session, video, background_tasks, settings)
    session.refresh(video)
    return _to_out(video)


@router.get("/videos", response_model=list[VideoOut])
def list_videos(session: Session = Depends(get_session)) -> list[VideoOut]:
    rows = session.exec(select(Video).order_by(Video.created_at.desc())).all()
    return [_to_out(row) for row in rows]


@router.get("/videos/{video_id}", response_model=VideoOut)
def get_video(video_id: uuid.UUID, session: Session = Depends(get_session)) -> VideoOut:
    video = session.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="video not found")
    return _to_out(video)


@router.get("/videos/{video_id}/file")
def get_video_file(
    video_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> FileResponse:
    video = session.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="video not found")
    path = Path(video.path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    media_type = mimetypes.guess_type(video.original_filename)[0] or "application/octet-stream"
    return FileResponse(
        path=path,
        filename=video.original_filename,
        media_type=media_type,
        content_disposition_type="inline",
    )


@router.delete("/videos/{video_id}", status_code=204)
def delete_video(
    video_id: uuid.UUID,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    video = session.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="video not found")
    folder = video_folder(settings.data_dir, video_id)
    session.delete(video)
    session.commit()
    remove_folder(folder)
    return Response(status_code=204)
