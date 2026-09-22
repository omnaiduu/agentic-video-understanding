from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.agent.client import Brain, FakeBrain, UnconfiguredBrain, VllmBrain, build_brain
from app.agent.loop import LoopError, LoopResult, run_loop
from app.agent.memory import HISTORY_KINDS, collect_windows, push_windows
from app.db import get_engine, get_session
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

# Latest finished turn per session, so a phone that loses the open request can
# pick the answer up with a short poll. The GPU work keeps running either way.
_results: dict[str, dict[str, Any]] = {}
_PING_SECONDS = 5


class ChatIn(BaseModel):
    message: str = Field(min_length=1)
    session_id: uuid.UUID | None = None
    thinking: bool | None = None


class StepOut(BaseModel):
    do: str
    start_s: float | None = None
    end_s: float | None = None
    ok: bool = True
    detail: str = ""


class ThoughtOut(BaseModel):
    do: str
    text: str


class ChatOut(BaseModel):
    answer: str
    citations: list[float]
    steps: list[StepOut]
    session_id: uuid.UUID
    export_url: str | None = None
    thinking: bool = False
    thoughts: list[ThoughtOut] = Field(default_factory=list)


def get_brain(settings: Settings = Depends(get_settings)) -> Brain:
    try:
        return build_brain(settings)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _want_thinking(payload: ChatIn, settings: Settings) -> bool:
    if payload.thinking is None:
        return settings.gemma_thinking
    return payload.thinking


def _brain_for_turn(injected: Brain, thinking: bool, settings: Settings) -> Brain:
    if not thinking:
        return injected
    if isinstance(injected, (FakeBrain, UnconfiguredBrain)):
        return injected
    if isinstance(injected, VllmBrain) and injected.thinking:
        return injected
    try:
        return build_brain(settings, thinking=True)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _thoughts(result: LoopResult, thinking: bool) -> list[ThoughtOut]:
    if not thinking:
        return []
    out: list[ThoughtOut] = []
    for step in result.steps:
        text = (step.reasoning or "").strip()
        if text:
            out.append(ThoughtOut(do=step.do, text=text))
    return out


def _history(session: Session, chat: ChatSession) -> list[tuple[str, str]]:
    rows = session.exec(
        select(ChatMessage)
        .where(ChatMessage.session_id == chat.id)
        .order_by(ChatMessage.created_at)
    ).all()
    return [(row.role, row.content) for row in rows if row.kind in HISTORY_KINDS]


def _log_debug_question(
    data_dir: Path,
    *,
    video_id: uuid.UUID,
    session_id: uuid.UUID,
    question: str,
    thinking: bool,
) -> None:
    path = data_dir / "debug-questions.jsonl"
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "video_id": str(video_id),
        "session_id": str(session_id),
        "question": question,
        "thinking": thinking,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        return


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


def _remember(session_id: uuid.UUID, question: str, out: ChatOut) -> None:
    data = out.model_dump(mode="json")
    data["status"] = "done"
    data["question"] = question
    _results[str(session_id)] = data


def _ping(session_id: uuid.UUID | None) -> bytes:
    body: dict[str, Any] = {"event": "ping", "pad": " " * 1024}
    if session_id is not None:
        body["session_id"] = str(session_id)
    return (json.dumps(body) + "\n").encode()


def _ensure_chat(
    session: Session,
    video: Video,
    session_id: uuid.UUID | None,
) -> ChatSession:
    if session_id is None:
        chat_row = ChatSession(video_id=video.id)
        session.add(chat_row)
        session.commit()
        session.refresh(chat_row)
        return chat_row
    chat_row = session.get(ChatSession, session_id)
    if chat_row is None or chat_row.video_id != video.id:
        raise HTTPException(status_code=404, detail="session not found")
    return chat_row


def _run_turn(
    session: Session,
    video: Video,
    chat_row: ChatSession,
    payload: ChatIn,
    brain: Brain,
    settings: Settings,
    embedder: Embedder,
    visual_embedder: VisualEmbedder,
    audio_embedder: AudioEmbedder,
    slide_embedder: SlideEmbedder,
) -> ChatOut:
    want_thinking = _want_thinking(payload, settings)
    brain = _brain_for_turn(brain, want_thinking, settings)
    history = _history(session, chat_row)
    last_times = list(chat_row.last_times or [])
    _log_debug_question(
        settings.data_dir,
        video_id=video.id,
        session_id=chat_row.id,
        question=payload.message,
        thinking=want_thinking,
    )

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
    out = ChatOut(
        answer=result.answer,
        citations=result.citations,
        steps=[StepOut.model_validate(step, from_attributes=True) for step in result.steps],
        session_id=chat_row.id,
        export_url=result.export_url,
        thinking=want_thinking,
        thoughts=_thoughts(result, want_thinking),
    )
    _remember(chat_row.id, payload.message, out)
    return out


def _load_ready(session: Session, video_id: uuid.UUID) -> Video:
    video = session.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="video not found")
    if video.status != VideoStatus.ready.value:
        raise HTTPException(status_code=409, detail="video is not ready")
    return video


@router.post("/videos/{video_id}/chat", response_model=ChatOut)
def chat(
    video_id: uuid.UUID,
    payload: ChatIn,
    session: Session = Depends(get_session),
    brain: Brain = Depends(get_brain),
    settings: Settings = Depends(get_settings),
    embedder: Embedder = Depends(get_embedder),
    visual_embedder: VisualEmbedder = Depends(get_visual_embedder),
    audio_embedder: AudioEmbedder = Depends(get_audio_embedder),
    slide_embedder: SlideEmbedder = Depends(get_slide_embedder),
) -> ChatOut:
    video = _load_ready(session, video_id)
    chat_row = _ensure_chat(session, video, payload.session_id)
    return _run_turn(
        session,
        video,
        chat_row,
        payload,
        brain,
        settings,
        embedder,
        visual_embedder,
        audio_embedder,
        slide_embedder,
    )


@router.post("/videos/{video_id}/chat/stream")
def chat_stream(
    video_id: uuid.UUID,
    payload: ChatIn,
    session: Session = Depends(get_session),
    brain: Brain = Depends(get_brain),
    settings: Settings = Depends(get_settings),
    embedder: Embedder = Depends(get_embedder),
    visual_embedder: VisualEmbedder = Depends(get_visual_embedder),
    audio_embedder: AudioEmbedder = Depends(get_audio_embedder),
    slide_embedder: SlideEmbedder = Depends(get_slide_embedder),
) -> StreamingResponse:
    """Send a byte immediately, then a ping every few seconds.

    A phone tunnel drops a chat POST that stays silent for about 30 seconds.
    The model keeps running; the pings hold the connection open.
    """
    video = _load_ready(session, video_id)
    chat_row = _ensure_chat(session, video, payload.session_id)
    session.commit()
    bound = payload.model_copy(update={"session_id": chat_row.id})
    sid = chat_row.id
    vid = video.id

    def generate():
        yield _ping(sid)
        holder: dict[str, Any] = {}

        def work() -> None:
            with Session(get_engine()) as db:
                fresh_video = db.get(Video, vid)
                fresh_chat = db.get(ChatSession, sid)
                if fresh_video is None or fresh_chat is None:
                    holder["error"] = (404, "video not found")
                    return
                try:
                    holder["out"] = _run_turn(
                        db,
                        fresh_video,
                        fresh_chat,
                        bound,
                        brain,
                        settings,
                        embedder,
                        visual_embedder,
                        audio_embedder,
                        slide_embedder,
                    )
                except HTTPException as exc:
                    detail = exc.detail if isinstance(exc.detail, str) else "chat failed"
                    holder["error"] = (exc.status_code, detail)

        worker = threading.Thread(target=work, name="chat-stream", daemon=True)
        worker.start()
        while worker.is_alive():
            worker.join(_PING_SECONDS)
            if worker.is_alive():
                yield _ping(sid)
        if "error" in holder:
            code, detail = holder["error"]
            yield (
                json.dumps({"event": "error", "status": code, "detail": detail}) + "\n"
            ).encode()
            return
        done = holder["out"].model_dump(mode="json")
        done["event"] = "done"
        done["status"] = "done"
        yield (json.dumps(done) + "\n").encode()

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/videos/{video_id}/chat/{session_id}/result")
def chat_result(
    video_id: uuid.UUID,
    session_id: uuid.UUID,
    message: str,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    chat_row = session.get(ChatSession, session_id)
    if chat_row is None or chat_row.video_id != video_id:
        raise HTTPException(status_code=404, detail="session not found")
    saved = _results.get(str(session_id))
    if saved is None or saved.get("question") != message:
        return {"status": "pending"}
    return saved
