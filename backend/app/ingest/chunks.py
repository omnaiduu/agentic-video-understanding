"""3s / 1.5s-hop wav slices for the sound index. Not the 30s listen cap."""

from __future__ import annotations

import audioop
import json
import subprocess
import tarfile
import wave
from dataclasses import dataclass
from pathlib import Path

from app.ingest.audio import IngestError

CHUNK_S = 3.0
HOP_S = 1.5
CLAP_RATE = 48000
WAV_MAGIC = b"RIFF"


@dataclass(frozen=True)
class IndexChunk:
    start_s: float
    end_s: float
    path: Path
    wav: bytes


def ingest_chunks_dir(folder: Path) -> Path:
    return folder / "ingest_chunks"


def chunks_tar_path(folder: Path) -> Path:
    return folder / "ingest_chunks.tar"


def clap_wav_path(folder: Path) -> Path:
    return folder / "clap.wav"


def extract_clap_audio(source: str | Path, dest: str | Path) -> Path:
    """Write the whole audio track at 48 kHz. Do not use get_audio (30s cap)."""
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
                str(CLAP_RATE),
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


def wav_is_mute(path: str | Path) -> bool:
    """True when the PCM is silence. Mute files skip the sound index."""
    with wave.open(str(path), "rb") as handle:
        n_frames = handle.getnframes()
        if n_frames <= 0:
            return True
        width = handle.getsampwidth()
        raw = handle.readframes(n_frames)
    return audioop.rms(raw, width) == 0


def slice_index_chunks(source_wav: str | Path, dest_dir: str | Path) -> list[IndexChunk]:
    """Cut 3s windows every 1.5s. ffmpeg already extracted the full track."""
    src = Path(source_wav)
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    with wave.open(str(src), "rb") as handle:
        params = handle.getparams()
        rate = handle.getframerate()
        n_frames = handle.getnframes()
        raw = handle.readframes(n_frames)
    if rate <= 0 or n_frames <= 0:
        raise IngestError("ffmpeg produced empty clap audio")
    duration_s = n_frames / rate
    frame_width = params.sampwidth * params.nchannels
    chunks: list[IndexChunk] = []
    index = 0
    start_s = 0.0
    while start_s < duration_s - 1e-9:
        end_s = min(start_s + CHUNK_S, duration_s)
        start_frame = int(round(start_s * rate))
        end_frame = min(int(round(end_s * rate)), n_frames)
        if end_frame <= start_frame:
            break
        piece = raw[start_frame * frame_width : end_frame * frame_width]
        path = dest / f"chunk_{index:06d}.wav"
        with wave.open(str(path), "wb") as out:
            out.setparams(params)
            out.writeframes(piece)
        data = path.read_bytes()
        if not data.startswith(WAV_MAGIC):
            raise IngestError("ingest did not write wav chunks")
        chunks.append(
            IndexChunk(start_s=start_s, end_s=end_s, path=path, wav=data)
        )
        index += 1
        start_s += HOP_S
    if not chunks:
        raise IngestError("ffmpeg produced no index chunks")
    manifest = [
        {
            "file": chunk.path.name,
            "start_s": chunk.start_s,
            "end_s": chunk.end_s,
        }
        for chunk in chunks
    ]
    (dest / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return chunks


def pack_index_chunks(dest_dir: Path, tar_path: Path) -> Path:
    tar_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_path, "w") as tar:
        for path in sorted(dest_dir.iterdir()):
            tar.add(path, arcname=path.name)
    return tar_path
