"""Cut a short 16 kHz mono wav. Caps before ffmpeg."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import app.tools.ffmpeg_cli as ffmpeg_cli
from app.tools.caps import (
    ScissorsError,
    require_audio_span,
    require_inside_file,
    require_window,
)
from app.tools.meta import get_meta


def get_audio(path: str | Path, start_s: float, end_s: float) -> bytes:
    span_s = require_window(start_s, end_s)
    require_audio_span(span_s)

    meta = get_meta(path)
    if not meta.has_audio:
        raise ScissorsError("file has no audio stream")
    require_inside_file(start_s, end_s, meta.duration_s)

    with TemporaryDirectory(prefix="scissors-audio-") as tmp:
        wav_path = Path(tmp) / "slice.wav"
        ffmpeg_cli.run_ffmpeg(
            [
                "-ss",
                ffmpeg_cli.format_seconds(start_s),
                "-i",
                str(path),
                "-t",
                ffmpeg_cli.format_seconds(span_s),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(wav_path),
            ]
        )
        if not wav_path.is_file():
            raise ScissorsError("ffmpeg produced no audio")
        return wav_path.read_bytes()
