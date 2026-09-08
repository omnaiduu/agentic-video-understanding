"""Re-encode a kept mp4/wav for the human. Caps before ffmpeg. Not temp scissors."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlmodel import Session

import app.tools.ffmpeg_cli as ffmpeg_cli
from app.models import Export, Video
from app.tools.caps import (
    ScissorsError,
    require_export_span,
    require_inside_file,
    require_window,
)
from app.tools.meta import get_meta

CLIP_KIND = "clip"
AUDIO_KIND = "audio"


@dataclass(frozen=True)
class ExportResult:
    id: uuid.UUID
    kind: str
    start_s: float
    end_s: float
    path: Path
    url: str


def export_url(video_id: uuid.UUID, export_id: uuid.UUID) -> str:
    return f"/videos/{video_id}/exports/{export_id}"


def exports_dir(source: str | Path) -> Path:
    return Path(source).parent / "exports"


def _unlink(path: Path) -> None:
    if path.is_file():
        path.unlink()


def _cut_window(path: str | Path, start_s: float, end_s: float) -> float:
    span_s = require_window(start_s, end_s)
    require_export_span(span_s)
    return span_s


def export_clip(
    path: str | Path,
    start_s: float,
    end_s: float,
    dest: str | Path,
) -> Path:
    span_s = _cut_window(path, start_s, end_s)
    meta = get_meta(path)
    if not meta.has_video:
        raise ScissorsError("file has no video stream")
    require_inside_file(start_s, end_s, meta.duration_s)

    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    args = [
        "-ss",
        ffmpeg_cli.format_seconds(start_s),
        "-i",
        str(path),
        "-t",
        ffmpeg_cli.format_seconds(span_s),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
    ]
    if meta.has_audio:
        args.extend(["-c:a", "aac"])
    else:
        args.append("-an")
    args.append(str(dest_path))
    try:
        ffmpeg_cli.run_ffmpeg(args)
    except Exception:
        _unlink(dest_path)
        raise
    if not dest_path.is_file() or dest_path.stat().st_size == 0:
        _unlink(dest_path)
        raise ScissorsError("ffmpeg produced no clip")
    return dest_path


def export_audio(
    path: str | Path,
    start_s: float,
    end_s: float,
    dest: str | Path,
) -> Path:
    span_s = _cut_window(path, start_s, end_s)
    meta = get_meta(path)
    if not meta.has_audio:
        raise ScissorsError("file has no audio stream")
    require_inside_file(start_s, end_s, meta.duration_s)

    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        ffmpeg_cli.run_ffmpeg(
            [
                "-ss",
                ffmpeg_cli.format_seconds(start_s),
                "-i",
                str(path),
                "-t",
                ffmpeg_cli.format_seconds(span_s),
                "-vn",
                "-c:a",
                "pcm_s16le",
                str(dest_path),
            ]
        )
    except Exception:
        _unlink(dest_path)
        raise
    if not dest_path.is_file() or dest_path.stat().st_size == 0:
        _unlink(dest_path)
        raise ScissorsError("ffmpeg produced no audio")
    return dest_path


def create_export(
    session: Session,
    video: Video,
    kind: str,
    start_s: float,
    end_s: float,
) -> ExportResult:
    if kind not in (CLIP_KIND, AUDIO_KIND):
        raise ScissorsError(f"unknown export kind {kind}")
    export_id = uuid.uuid4()
    ext = "mp4" if kind == CLIP_KIND else "wav"
    dest = exports_dir(video.path) / f"{export_id}.{ext}"
    if kind == CLIP_KIND:
        export_clip(video.path, start_s, end_s, dest)
    else:
        export_audio(video.path, start_s, end_s, dest)
    row = Export(
        id=export_id,
        video_id=video.id,
        kind=kind,
        start_s=start_s,
        end_s=end_s,
        path=str(dest),
    )
    session.add(row)
    session.commit()
    return ExportResult(
        id=export_id,
        kind=kind,
        start_s=start_s,
        end_s=end_s,
        path=dest,
        url=export_url(video.id, export_id),
    )
