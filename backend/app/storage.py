from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile

CHUNK_SIZE = 1024 * 1024


class OversizeError(Exception):
    """Raised when a copy exceeds MAX_UPLOAD_BYTES."""


def video_folder(data_dir: Path, video_id: uuid.UUID) -> Path:
    return data_dir / "videos" / str(video_id)


def original_dest(folder: Path, filename: str) -> Path:
    suffix = Path(safe_filename(filename)).suffix
    return folder / f"original{suffix}"


def safe_filename(name: str | None) -> str:
    base = Path(name or "upload").name
    if base in ("", ".", ".."):
        return "upload"
    return base


def remove_folder(folder: Path) -> None:
    if folder.exists():
        shutil.rmtree(folder)


async def save_upload(upload: UploadFile, dest: Path, max_bytes: int) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    try:
        with dest.open("wb") as out:
            while True:
                chunk = await upload.read(CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise OversizeError()
                out.write(chunk)
    except OversizeError:
        remove_folder(dest.parent)
        raise
    except Exception:
        remove_folder(dest.parent)
        raise
    return total


def copy_file(source: Path, dest: Path, max_bytes: int) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    try:
        with source.open("rb") as inf, dest.open("wb") as out:
            while True:
                chunk = inf.read(CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise OversizeError()
                out.write(chunk)
    except OversizeError:
        remove_folder(dest.parent)
        raise
    except Exception:
        remove_folder(dest.parent)
        raise
    return total
