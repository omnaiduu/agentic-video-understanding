from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.agent.client import Brain, build_brain
from app.agent.loop import LoopError, LoopResult, run_loop
from app.agent.memory import HISTORY_KINDS, collect_windows, push_windows
from app.db import get_session
from app.models import ChatMessage, ChatSession, Video, VideoStatus
from app.search.audio import search_audio
from app.search.clap import AudioEmbedder, get_audio_embedder
from app.search.colqwen import SlideEmbedder, get_slide_embedder
from app.search.embed import Embedder, get_embedder
from app.search.siglip import VisualEmbedder, get_visual_embedder
from app.search.slides import search_slides
from app.search.transcript import search_transcript
from app.search.visual import search_visual
from app.settings import Settings, get_settings
from app.tools.export import create_export

router = APIRouter()


class ChatIn(BaseModel):
    message: str = Field(min_length=1)
    session_id: uuid.UUID | None = None


class StepOut(BaseModel):
    do: str
    start_s: float | None = None
    end_s: float | None = None
    ok: bool = True
    detail: str = ""


class ChatOut(BaseModel):
    answer: str
    citations: list[float]
    steps: list[StepOut]
    session_id: uuid.UUID
    export_url: str | None = None


def get_brain(settings: Settings = Depends(get_settings)) -> Brain:
    try:
        return build_brain(settings)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _history(session: Session, chat: ChatSession) -> list[tuple[str, str]]:
    rows = session.exec(
        select(ChatMessage)
        .where(ChatMessage.session_id == chat.id)
        .order_by(ChatMessage.created_at)
    ).all()
    return [(row.role, row.content) for row in rows if row.kind in HISTORY_KINDS]


def _save_turn(
    session: Session,
    chat: ChatSession,
    question: str,
    result: LoopResult,
) -> None:
    session.add(
        ChatMessage(
            session_id=chat.id,
            role="user",
            kind="question",
            content=question,
            shown_times=None,
        )
    )
    for step in result.steps:
        times: list[float] | None = None
        if step.start_s is not None and step.end_s is not None:
            times = [step.start_s, step.end_s]
        session.add(
            ChatMessage(
                session_id=chat.id,
                role="assistant" if step.do == "answer" else "user",
                kind=step.do,
                content=step.detail or step.do,
                shown_times=times,
            )
        )
    row = session.get(ChatSession, chat.id)
    if row is not None:
        row.last_times = push_windows(row.last_times, collect_windows(result.steps))
        session.add(row)
    session.commit()


@router.post("/videos/{video_id}/chat", response_model=ChatOut)
def chat(
    video_id: uuid.UUID,
    payload: ChatIn,
    session: Session = Depends(get_session),
    brain: Brain = Depends(get_brain),
    embedder: Embedder = Depends(get_embedder),
    visual_embedder: VisualEmbedder = Depends(get_visual_embedder),
    audio_embedder: AudioEmbedder = Depends(get_audio_embedder),
    slide_embedder: SlideEmbedder = Depends(get_slide_embedder),
) -> ChatOut:
    video = session.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="video not found")
    if video.status != VideoStatus.ready.value:
        raise HTTPException(status_code=409, detail="video is not ready")

    if payload.session_id is None:
        chat_row = ChatSession(video_id=video.id)
        session.add(chat_row)
        session.commit()
        session.refresh(chat_row)
    else:
        chat_row = session.get(ChatSession, payload.session_id)
        if chat_row is None or chat_row.video_id != video.id:
            raise HTTPException(status_code=404, detail="session not found")

    history = _history(session, chat_row)
    last_times = list(chat_row.last_times or [])

    def _search(query: str):
        return search_transcript(session, video.id, query, embedder)

    def _search_visual(query: str):
        return search_visual(session, video.id, query, visual_embedder)

    def _search_audio(query: str):
        return search_audio(session, video.id, query, audio_embedder)

    def _search_slides(query: str):
        return search_slides(session, video.id, query, slide_embedder)

    def _export_clip(start_s: float, end_s: float):
        return create_export(session, video, "clip", start_s, end_s)

    def _export_audio(start_s: float, end_s: float):
        return create_export(session, video, "audio", start_s, end_s)

    try:
        result = run_loop(
            video.path,
            payload.message,
            brain,
            search=_search,
            search_visual=_search_visual,
            search_audio=_search_audio,
            search_slides=_search_slides,
            export_clip=_export_clip,
            export_audio=_export_audio,
            transcript_status=video.transcript_status,
            visual_status=video.visual_status,
            audio_status=video.audio_status,
            slides_status=video.slides_status,
            history=history,
            last_times=last_times,
        )
    except LoopError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    _save_turn(session, chat_row, payload.message, result)
    return ChatOut(
        answer=result.answer,
        citations=result.citations,
        steps=[StepOut.model_validate(step, from_attributes=True) for step in result.steps],
        session_id=chat_row.id,
        export_url=result.export_url,
    )
