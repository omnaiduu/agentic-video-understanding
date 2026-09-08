from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.agent.client import Brain, build_brain
from app.agent.loop import LoopError, LoopResult, run_loop
from app.db import get_session
from app.models import ChatMessage, ChatSession, Video, VideoStatus
from app.search.embed import Embedder, get_embedder
from app.search.siglip import VisualEmbedder, get_visual_embedder
from app.search.transcript import search_transcript
from app.search.visual import search_visual
from app.settings import Settings, get_settings

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


def get_brain(settings: Settings = Depends(get_settings)) -> Brain:
    try:
        return build_brain(settings)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _save_turn(
    session: Session,
    chat: ChatSession,
    question: str,
    result: LoopResult,
) -> None:
    session.add(
        ChatMessage(session_id=chat.id, role="user", content=question, shown_times=None)
    )
    for step in result.steps:
        times: list[float] | None = None
        if step.start_s is not None and step.end_s is not None:
            times = [step.start_s, step.end_s]
        session.add(
            ChatMessage(
                session_id=chat.id,
                role="assistant" if step.do == "answer" else "user",
                content=step.detail or step.do,
                shown_times=times,
            )
        )
    session.commit()


@router.post("/videos/{video_id}/chat", response_model=ChatOut)
def chat(
    video_id: uuid.UUID,
    payload: ChatIn,
    session: Session = Depends(get_session),
    brain: Brain = Depends(get_brain),
    embedder: Embedder = Depends(get_embedder),
    visual_embedder: VisualEmbedder = Depends(get_visual_embedder),
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

    def _search(query: str):
        return search_transcript(session, video.id, query, embedder)

    def _search_visual(query: str):
        return search_visual(session, video.id, query, visual_embedder)

    try:
        result = run_loop(
            video.path,
            payload.message,
            brain,
            search=_search,
            search_visual=_search_visual,
            transcript_status=video.transcript_status,
            visual_status=video.visual_status,
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
    )
