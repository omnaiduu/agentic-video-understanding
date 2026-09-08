"""Cut a few JPEG frames from a stored video. Caps before ffmpeg."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import app.tools.ffmpeg_cli as ffmpeg_cli
from app.tools.caps import (
    ScissorsError,
    planned_frame_count,
    require_frame_count,
    require_inside_file,
    require_window,
    resolve_fps,
)
from app.tools.meta import get_meta

JPEG_MAGIC = b"\xff\xd8\xff"


@dataclass(frozen=True)
class Frame:
    t: float
    jpeg: bytes


def get_frames(
    path: str | Path,
    start_s: float,
    end_s: float,
    fps: float | None = None,
) -> list[Frame]:
    span_s = require_window(start_s, end_s)
    rate = resolve_fps(span_s, fps)
    require_frame_count(span_s, rate)
    count = planned_frame_count(span_s, rate)

    meta = get_meta(path)
    if not meta.has_video:
        raise ScissorsError("file has no video stream")
    require_inside_file(start_s, end_s, meta.duration_s)

    with TemporaryDirectory(prefix="scissors-frames-") as tmp:
        pattern = str(Path(tmp) / "frame_%04d.jpg")
        ffmpeg_cli.run_ffmpeg(
            [
                "-ss",
                ffmpeg_cli.format_seconds(start_s),
                "-i",
                str(path),
                "-t",
                ffmpeg_cli.format_seconds(span_s),
                "-an",
                "-vf",
                f"fps={rate}",
                "-frames:v",
                str(count),
                "-q:v",
                "2",
                pattern,
            ]
        )
        files = sorted(Path(tmp).glob("frame_*.jpg"))
        if not files:
            raise ScissorsError("ffmpeg produced no frames")
        frames: list[Frame] = []
        for index, file in enumerate(files[:count]):
            data = file.read_bytes()
            if not data.startswith(JPEG_MAGIC):
                raise ScissorsError("ffmpeg did not write JPEG frames")
            frames.append(Frame(t=start_s + index / rate, jpeg=data))
        return frames
