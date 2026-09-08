"""Caps and window checks. Count before any ffmpeg extract."""

from __future__ import annotations

import math


MAX_FRAMES = 64
MAX_AUDIO_SECONDS = 30.0
SHORT_SPAN_S = 8.0
DEFAULT_SHORT_FPS = 4.0
DEFAULT_LONG_FPS = 1.0
DURATION_SLOP_S = 1e-3


class ScissorsError(Exception):
    """Invalid cut, missing stream, or ffmpeg extract failed."""


def require_window(start_s: float, end_s: float) -> float:
    if not math.isfinite(start_s) or not math.isfinite(end_s):
        raise ScissorsError("start and end must be finite numbers")
    if start_s < 0:
        raise ScissorsError("start must be >= 0")
    if end_s <= start_s:
        raise ScissorsError("end must be after start")
    return end_s - start_s


def resolve_fps(span_s: float, fps: float | None) -> float:
    if fps is None:
        if span_s <= SHORT_SPAN_S:
            return DEFAULT_SHORT_FPS
        return DEFAULT_LONG_FPS
    if not math.isfinite(fps) or fps <= 0:
        raise ScissorsError("fps must be a positive number")
    return fps


def require_frame_count(span_s: float, fps: float) -> None:
    requested = span_s * fps
    if requested > MAX_FRAMES:
        raise ScissorsError(
            f"requested {requested:.1f} frames ({span_s:.3f}s × {fps:g} fps); "
            f"cap is {MAX_FRAMES}. Refuse, do not shrink."
        )


def require_audio_span(span_s: float) -> None:
    if span_s > MAX_AUDIO_SECONDS:
        raise ScissorsError(
            f"requested {span_s:.3f}s of audio; cap is {MAX_AUDIO_SECONDS:.0f}s. "
            "Refuse, do not shrink."
        )


def planned_frame_count(span_s: float, fps: float) -> int:
    return max(1, min(MAX_FRAMES, math.ceil(span_s * fps - 1e-12)))


def require_inside_file(start_s: float, end_s: float, duration_s: float) -> None:
    if start_s >= duration_s:
        raise ScissorsError("start is past the end of the file")
    if end_s > duration_s + DURATION_SLOP_S:
        raise ScissorsError("end is past the end of the file")
