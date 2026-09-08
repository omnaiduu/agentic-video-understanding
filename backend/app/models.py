import uuid
from datetime import datetime, timezone
from enum import Enum

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Text
from sqlmodel import Field, SQLModel


class VideoKind(str, Enum):
    video = "video"
    audio = "audio"


class VideoStatus(str, Enum):
    uploaded = "uploaded"
    processing = "processing"
    ready = "ready"
    error = "error"


class IndexStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    ready = "ready"
    error = "error"
    skipped = "skipped"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Video(SQLModel, table=True):
    __tablename__ = "videos"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    original_filename: str
    path: str
    kind: str = VideoKind.video.value
    duration_s: float | None = None
    fps: float | None = None
    has_audio: bool = False
    has_video: bool = False
    status: str = VideoStatus.uploaded.value
    transcript_status: str = IndexStatus.pending.value
    visual_status: str = IndexStatus.pending.value
    audio_status: str = IndexStatus.pending.value
    error_message: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(
        default_factory=_utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class ChatSession(SQLModel, table=True):
    __tablename__ = "chat_sessions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    video_id: uuid.UUID = Field(
        sa_column=Column(
            sa.Uuid(),
            sa.ForeignKey("videos.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    created_at: datetime = Field(
        default_factory=_utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    last_times: list[dict] = Field(
        default_factory=list,
        sa_column=Column(sa.JSON, nullable=False),
    )


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_messages"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(
        sa_column=Column(
            sa.Uuid(),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    role: str
    kind: str = "question"
    content: str = Field(sa_column=Column(Text, nullable=False))
    shown_times: list[float] | None = Field(default=None, sa_column=Column(sa.JSON, nullable=True))
    created_at: datetime = Field(
        default_factory=_utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class TranscriptLine(SQLModel, table=True):
    __tablename__ = "transcript_lines"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    video_id: uuid.UUID = Field(
        sa_column=Column(
            sa.Uuid(),
            sa.ForeignKey("videos.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    start_s: float
    end_s: float
    text: str = Field(sa_column=Column(Text, nullable=False))
    embedding: list[float] | None = Field(
        default=None,
        sa_column=Column(Vector(384), nullable=True),
    )


class VisualFrame(SQLModel, table=True):
    __tablename__ = "visual_frames"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    video_id: uuid.UUID = Field(
        sa_column=Column(
            sa.Uuid(),
            sa.ForeignKey("videos.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    t_s: float
    embedding: list[float] | None = Field(
        default=None,
        sa_column=Column(Vector(1152), nullable=True),
    )


class Export(SQLModel, table=True):
    __tablename__ = "exports"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    video_id: uuid.UUID = Field(
        sa_column=Column(
            sa.Uuid(),
            sa.ForeignKey("videos.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    kind: str
    start_s: float
    end_s: float
    path: str
    created_at: datetime = Field(
        default_factory=_utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class AudioChunk(SQLModel, table=True):
    __tablename__ = "audio_chunks"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    video_id: uuid.UUID = Field(
        sa_column=Column(
            sa.Uuid(),
            sa.ForeignKey("videos.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    start_s: float
    end_s: float
    embedding: list[float] | None = Field(
        default=None,
        sa_column=Column(Vector(512), nullable=True),
    )


class VideoOut(SQLModel):
    id: uuid.UUID
    original_filename: str
    path: str
    kind: str
    duration_s: float | None
    fps: float | None
    has_audio: bool
    has_video: bool
    status: str
    transcript_status: str
    visual_status: str
    audio_status: str
    error_message: str | None
    created_at: datetime
