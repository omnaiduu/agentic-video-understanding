"""Full-file 16 kHz mono wav for Whisper. Not the 30s listen cap."""

from __future__ import annotations

import subprocess
from pathlib import Path


class IngestError(Exception):
    """Full-file audio extract failed. File on disk stays; timed look still works."""


def extract_full_audio(source: str | Path, dest: str | Path) -> Path:
    """Write the whole audio track. Do not use get_audio (that tool caps at 30s)."""
    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-nostdin",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(source),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(dest_path),
            ],
            check=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise IngestError("ffmpeg is not installed") from exc
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or b"").decode("utf-8", errors="replace").strip()
        detail = err.splitlines()[-1][:500] if err else "ffmpeg failed"
        raise IngestError(detail) from exc
    if not dest_path.is_file() or dest_path.stat().st_size == 0:
        raise IngestError("ffmpeg produced no audio")
    return dest_path
