"""File measurements for planning a cut. Wraps Phase 1 ffprobe."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.media.probe import ProbeError, probe
from app.tools.caps import ScissorsError


@dataclass(frozen=True)
class VideoMeta:
    duration_s: float
    fps: float | None
    has_audio: bool
    has_video: bool


def get_meta(path: str | Path) -> VideoMeta:
    file_path = Path(path)
    if not file_path.is_file():
        raise ScissorsError(f"file not found: {file_path}")
    try:
        result = probe(file_path)
    except ProbeError as exc:
        raise ScissorsError(str(exc)) from exc
    return VideoMeta(
        duration_s=result.duration_s,
        fps=result.fps,
        has_audio=result.has_audio,
        has_video=result.has_video,
    )
