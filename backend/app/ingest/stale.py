"""Flip books that never got a Modal callback from processing to error."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models import IndexStatus, Video

# Modal ingest functions time out at 60 minutes. After that, "processing" is a lie.
STALE_PROCESSING_S = 70 * 60

_BOOKS = (
    "transcript_status",
    "visual_status",
    "audio_status",
    "slides_status",
)


def fail_stale_processing_indexes(
    video: Video,
    *,
    now: datetime | None = None,
    timeout_s: float = STALE_PROCESSING_S,
) -> bool:
    """Mark processing books as error when ingest has been running too long.

    Ingest starts at upload, so created_at is the start clock. Returns True if
    any book flipped.
    """
    started = video.created_at
    if started is None:
        return False
    clock = now or datetime.now(timezone.utc)
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    if clock.tzinfo is None:
        clock = clock.replace(tzinfo=timezone.utc)
    if (clock - started).total_seconds() < timeout_s:
        return False
    changed = False
    for name in _BOOKS:
        if getattr(video, name) == IndexStatus.processing.value:
            setattr(video, name, IndexStatus.error.value)
            changed = True
    return changed
