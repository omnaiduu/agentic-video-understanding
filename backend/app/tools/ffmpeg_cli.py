"""ffmpeg subprocess helper for cuts. Tests monkeypatch run_ffmpeg."""

from __future__ import annotations

import subprocess

from app.tools.caps import ScissorsError


def format_seconds(seconds: float) -> str:
    return f"{seconds:.6f}"


def _short_ffmpeg_error(exc: subprocess.CalledProcessError) -> str:
    stderr = exc.stderr
    if not stderr:
        return str(exc) or "ffmpeg failed"
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
        return "ffmpeg failed"
    return lines[-1][:500]


def run_ffmpeg(args: list[str]) -> None:
    try:
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostdin", "-y", "-loglevel", "error", *args],
            check=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise ScissorsError("ffmpeg is not installed") from exc
    except subprocess.CalledProcessError as exc:
        raise ScissorsError(_short_ffmpeg_error(exc)) from exc
