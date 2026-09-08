"""1 FPS JPEG extract for the picture index. Not the 64-frame look cap."""

from __future__ import annotations

import json
import subprocess
import tarfile
from dataclasses import dataclass
from pathlib import Path

from app.ingest.audio import IngestError

JPEG_MAGIC = b"\xff\xd8\xff"
INDEX_FPS = 1.0


@dataclass(frozen=True)
class IndexJpeg:
    t_s: float
    path: Path
    jpeg: bytes


def ingest_frames_dir(folder: Path) -> Path:
    return folder / "ingest_frames"


def frames_tar_path(folder: Path) -> Path:
    return folder / "ingest_frames.tar"


def extract_index_frames(source: str | Path, dest_dir: str | Path) -> list[IndexJpeg]:
    """Write ~1 JPEG per second. Do not use get_frames (that tool caps at 64 photos)."""
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    pattern = str(dest / "frame_%06d.jpg")
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
                "-an",
                "-vf",
                f"fps={INDEX_FPS:g}",
                "-q:v",
                "2",
                pattern,
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

    files = sorted(dest.glob("frame_*.jpg"))
    if not files:
        raise IngestError("ffmpeg produced no index frames")
    frames: list[IndexJpeg] = []
    for index, path in enumerate(files):
        data = path.read_bytes()
        if not data.startswith(JPEG_MAGIC):
            raise IngestError("ffmpeg did not write JPEG frames")
        frames.append(IndexJpeg(t_s=index / INDEX_FPS, path=path, jpeg=data))
    manifest = [{"file": frame.path.name, "t_s": frame.t_s} for frame in frames]
    (dest / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return frames


def pack_index_frames(dest_dir: Path, tar_path: Path) -> Path:
    tar_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_path, "w") as tar:
        for path in sorted(dest_dir.iterdir()):
            tar.add(path, arcname=path.name)
    return tar_path
