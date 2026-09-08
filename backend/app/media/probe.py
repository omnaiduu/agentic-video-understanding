"""ffprobe wrapper. ffmpeg/ffprobe must be installed on the host."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import ffmpeg


class ProbeError(Exception):
    """ffprobe could not read the file."""


@dataclass(frozen=True)
class ProbeResult:
    kind: str
    duration_s: float | None
    fps: float | None
    has_audio: bool
    has_video: bool


def _parse_rate(value: str | None) -> float | None:
    if not value or value == "0/0":
        return None
    try:
        if "/" in value:
            num_s, den_s = value.split("/", 1)
            den = float(den_s)
            if den == 0:
                return None
            return float(num_s) / den
        return float(value)
    except ValueError:
        return None


def _is_picture_stream(stream: dict) -> bool:
    disposition = stream.get("disposition") or {}
    return bool(disposition.get("attached_pic"))


def _short_probe_error(exc: Exception) -> str:
    stderr = getattr(exc, "stderr", None)
    if not stderr:
        return str(exc) or "ffprobe could not read this file"
    text = stderr.decode("utf-8", errors="replace") if isinstance(stderr, (bytes, bytearray)) else str(stderr)
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lower = stripped.lower()
        if lower.startswith(
            (
                "ffmpeg version",
                "ffprobe version",
                "built with",
                "configuration:",
                "libav",
                "libsw",
                "libpost",
            )
        ):
            continue
        lines.append(stripped)
    if not lines:
        return "ffprobe could not read this file"
    return lines[-1][:500]


def probe(path: Path) -> ProbeResult:
    try:
        info = ffmpeg.probe(str(path))
    except ffmpeg.Error as exc:
        raise ProbeError(_short_probe_error(exc)) from exc
    except FileNotFoundError as exc:
        raise ProbeError("ffprobe is not installed") from exc

    streams = info.get("streams") or []
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    video_streams = [
        s
        for s in streams
        if s.get("codec_type") == "video" and not _is_picture_stream(s)
    ]
    has_video = bool(video_streams)

    duration_s = None
    raw_duration = (info.get("format") or {}).get("duration")
    if raw_duration is not None:
        try:
            duration_s = float(raw_duration)
        except ValueError:
            duration_s = None

    fps = None
    if video_streams:
        fps = _parse_rate(video_streams[0].get("avg_frame_rate")) or _parse_rate(
            video_streams[0].get("r_frame_rate")
        )

    format_name = (info.get("format") or {}).get("format_name") or ""
    format_parts = {part.strip() for part in format_name.split(",") if part.strip()}

    if has_video:
        if "mp4" not in format_parts and path.suffix.lower() != ".mp4":
            raise ProbeError("video files must be mp4")
        kind = "video"
    elif has_audio:
        kind = "audio"
    else:
        raise ProbeError("file has no audio or video stream")

    if duration_s is None:
        raise ProbeError("ffprobe did not report a duration")

    return ProbeResult(
        kind=kind,
        duration_s=duration_s,
        fps=fps,
        has_audio=has_audio,
        has_video=has_video,
    )
