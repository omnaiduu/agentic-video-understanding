"""Unique-slide dedup on the 1 FPS stream. Not scene detect."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path

from app.ingest.audio import IngestError
from app.ingest.frames import INDEX_FPS, IndexJpeg

SAME_SLIDE_HAMMING = 8
HASH_PIXELS = 8
MEAN_DELTA = 12


@dataclass(frozen=True)
class UniqueSlide:
    t_start_s: float
    t_end_s: float
    path: Path
    jpeg: bytes
    phash: int
    mean: int


def ingest_slides_dir(folder: Path) -> Path:
    return folder / "ingest_slides"


def slides_tar_path(folder: Path) -> Path:
    return folder / "ingest_slides.tar"


def average_hash(jpeg_path: Path) -> tuple[int, int]:
    """8×8 average hash + brightness via ffmpeg. Same slide ≈ small Hamming + mean."""
    try:
        completed = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-nostdin",
                "-loglevel",
                "error",
                "-i",
                str(jpeg_path),
                "-an",
                "-vf",
                f"scale={HASH_PIXELS}:{HASH_PIXELS}:flags=bilinear,format=gray",
                "-f",
                "rawvideo",
                "-",
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
    pixels = completed.stdout[: HASH_PIXELS * HASH_PIXELS]
    if len(pixels) < HASH_PIXELS * HASH_PIXELS:
        raise IngestError("ffmpeg did not write a hash frame")
    mean = sum(pixels) / len(pixels)
    bits = 0
    for index, value in enumerate(pixels):
        if value >= mean:
            bits |= 1 << index
    return bits, int(round(mean))


def hamming(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def unique_slides(
    frames: list[IndexJpeg],
    *,
    max_hamming: int = SAME_SLIDE_HAMMING,
) -> list[UniqueSlide]:
    """Keep one JPEG + time span per near-duplicate run. Not PySceneDetect."""
    kept: list[UniqueSlide] = []
    step = 1.0 / INDEX_FPS
    for frame in frames:
        digest, mean = average_hash(frame.path)
        if (
            kept
            and abs(mean - kept[-1].mean) <= MEAN_DELTA
            and hamming(digest, kept[-1].phash) <= max_hamming
        ):
            kept[-1] = replace(kept[-1], t_end_s=frame.t_s + step)
            continue
        kept.append(
            UniqueSlide(
                t_start_s=frame.t_s,
                t_end_s=frame.t_s + step,
                path=frame.path,
                jpeg=frame.jpeg,
                phash=digest,
                mean=mean,
            )
        )
    return kept


def write_unique_slides(slides: list[UniqueSlide], dest_dir: Path) -> list[UniqueSlide]:
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    written: list[UniqueSlide] = []
    manifest: list[dict] = []
    for index, slide in enumerate(slides):
        name = f"slide_{index:06d}.jpg"
        path = dest / name
        path.write_bytes(slide.jpeg)
        written.append(replace(slide, path=path))
        manifest.append(
            {
                "file": name,
                "t_start_s": slide.t_start_s,
                "t_end_s": slide.t_end_s,
            }
        )
    (dest / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return written
