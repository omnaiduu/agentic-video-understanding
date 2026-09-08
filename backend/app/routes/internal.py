from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.db import get_session
from app.ingest.speech import full_wav_path, save_segments
from app.ingest.whisper import TranscriptSegment
from app.models import IndexStatus, Video
from app.search.embed import Embedder, get_embedder
from app.settings import Settings, get_settings

router = APIRouter()


class SegmentIn(BaseModel):
    start_s: float
    end_s: float
    text: str
    embedding: list[float] | None = None


class TranscriptIn(BaseModel):
    status: Literal["ready", "error"] = "ready"
    error_message: str | None = None
    segments: list[SegmentIn] = Field(default_factory=list)


def require_ingest_secret(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    secret = settings.ingest_secret
    if not secret:
        raise HTTPException(status_code=403, detail="ingest secret is not configured")
    auth = request.headers.get("authorization") or ""
    if auth != f"Bearer {secret}":
        raise HTTPException(status_code=403, detail="invalid ingest secret")


@router.get("/internal/videos/{video_id}/audio")
def get_ingest_audio(
    video_id: uuid.UUID,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_ingest_secret),
) -> FileResponse:
    video = session.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="video not found")
    path = full_wav_path(settings.data_dir, video.id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="audio not found")
    return FileResponse(
        path=path,
        filename="full.wav",
        media_type="audio/wav",
        content_disposition_type="inline",
    )


@router.post("/internal/videos/{video_id}/transcript")
def receive_transcript(
    video_id: uuid.UUID,
    payload: TranscriptIn,
    session: Session = Depends(get_session),
    embedder: Embedder = Depends(get_embedder),
    _: None = Depends(require_ingest_secret),
) -> dict:
    video = session.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="video not found")
    if video.transcript_status == IndexStatus.ready.value:
        return {"ok": True, "ignored": True}
    if payload.status == "error":
        video.transcript_status = IndexStatus.error.value
        session.add(video)
        session.commit()
        return {"ok": True}
    segments = [
        TranscriptSegment(start_s=row.start_s, end_s=row.end_s, text=row.text)
        for row in payload.segments
    ]
    embeddings = [row.embedding for row in payload.segments]
    save_segments(session, video, segments, embedder, embeddings)
    return {"ok": True, "lines": len(segments)}
