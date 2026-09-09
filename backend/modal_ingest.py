"""Modal ingest worker: faster-whisper turbo on L4. Not the chat GPU.

Laptop extracts the full audio track (no 30s listen cap), 1 FPS JPEGs, and
3s / 1.5s-hop wav chunks. This worker transcribes (faster-whisper turbo),
embeds pictures (SigLIP 2), embeds sounds (LAION-CLAP), and embeds unique
slides (ColQwen2.x).
It POSTs results to the laptop API and never opens laptop Postgres.

Deploy from backend/:

    modal deploy modal_ingest.py

Set INGEST=modal, PUBLIC_BASE_URL to a URL Modal can reach, INGEST_SECRET,
and EMBED_MODEL (default intfloat/e5-small-v2).
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import modal

MINUTES = 60
WHISPER_NAME = "turbo"
EMBED_NAME = "intfloat/e5-small-v2"

ingest_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "faster-whisper>=1.1.0",
        "sentence-transformers>=3.3.0",
        "httpx>=0.27.0",
    )
    .env({"HF_XET_HIGH_PERFORMANCE": "1"})
)

hf_cache_vol = modal.Volume.from_name("huggingface-cache", create_if_missing=True)

siglip_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "torch>=2.4.0",
        "transformers>=4.49.0",
        "pillow>=10.0.0",
        "httpx>=0.27.0",
    )
    .env({"HF_XET_HIGH_PERFORMANCE": "1"})
)

app = modal.App("agentic-video-ingest")


@app.function(
    image=ingest_image,
    gpu="L4",
    timeout=60 * MINUTES,
    scaledown_window=2 * MINUTES,
    volumes={"/root/.cache/huggingface": hf_cache_vol},
)
def transcribe_video(
    video_id: str,
    audio_url: str,
    callback_url: str,
    secret: str,
    whisper_model: str = WHISPER_NAME,
    embed_model: str = EMBED_NAME,
) -> None:
    import httpx
    from faster_whisper import WhisperModel
    from sentence_transformers import SentenceTransformer

    headers = {"Authorization": f"Bearer {secret}"}
    wav_bytes = httpx.get(audio_url, headers=headers, timeout=120.0).content
    with TemporaryDirectory(prefix="ingest-whisper-") as tmp:
        wav_path = Path(tmp) / "full.wav"
        wav_path.write_bytes(wav_bytes)
        model = WhisperModel(whisper_model, device="cuda", compute_type="float16")
        segments_iter, _info = model.transcribe(str(wav_path))
        segments = []
        for segment in segments_iter:
            text = (segment.text or "").strip()
            if not text:
                continue
            segments.append(
                {
                    "start_s": float(segment.start),
                    "end_s": float(segment.end),
                    "text": text,
                }
            )

    if segments:
        embedder = SentenceTransformer(embed_model)
        passages = ["passage: " + row["text"] for row in segments]
        matrix = embedder.encode(passages, normalize_embeddings=True)
        for row, vector in zip(segments, matrix):
            row["embedding"] = [float(x) for x in vector.tolist()]

    try:
        httpx.post(
            callback_url,
            headers=headers,
            json={"status": "ready", "segments": segments},
            timeout=120.0,
        ).raise_for_status()
    except Exception:
        httpx.post(
            callback_url,
            headers=headers,
            json={"status": "error", "error_message": "callback failed", "segments": []},
            timeout=30.0,
        )


SIGLIP_NAME = "google/siglip2-so400m-patch16-384"


@app.function(
    image=siglip_image,
    gpu="L4",
    timeout=60 * MINUTES,
    scaledown_window=2 * MINUTES,
    volumes={"/root/.cache/huggingface": hf_cache_vol},
)
def embed_visual(
    video_id: str,
    frames_url: str,
    callback_url: str,
    secret: str,
    siglip_model: str = SIGLIP_NAME,
) -> None:
    import io
    import json
    import tarfile
    from pathlib import Path
    from tempfile import TemporaryDirectory

    import httpx
    import torch
    from PIL import Image
    from transformers import AutoModel, AutoProcessor

    del video_id
    headers = {"Authorization": f"Bearer {secret}"}
    tar_bytes = httpx.get(frames_url, headers=headers, timeout=300.0).content
    frames: list[dict] = []
    try:
        with TemporaryDirectory(prefix="ingest-siglip-") as tmp:
            tar_path = Path(tmp) / "frames.tar"
            tar_path.write_bytes(tar_bytes)
            extract_dir = Path(tmp) / "frames"
            extract_dir.mkdir()
            with tarfile.open(tar_path, "r") as tar:
                tar.extractall(extract_dir, filter="data")
            manifest_path = extract_dir / "manifest.json"
            if manifest_path.is_file():
                items = json.loads(manifest_path.read_text(encoding="utf-8"))
            else:
                files = sorted(extract_dir.glob("frame_*.jpg"))
                items = [
                    {"file": path.name, "t_s": float(index)}
                    for index, path in enumerate(files)
                ]
            model = AutoModel.from_pretrained(siglip_model).eval()
            processor = AutoProcessor.from_pretrained(siglip_model)
            for item in items:
                jpeg_path = extract_dir / item["file"]
                if not jpeg_path.is_file():
                    continue
                image = Image.open(io.BytesIO(jpeg_path.read_bytes())).convert("RGB")
                inputs = processor(images=[image], return_tensors="pt")
                with torch.no_grad():
                    vector = model.get_image_features(**inputs)
                    vector = vector / vector.norm(p=2, dim=-1, keepdim=True)
                frames.append(
                    {
                        "t_s": float(item["t_s"]),
                        "embedding": [float(x) for x in vector[0].tolist()],
                    }
                )
        httpx.post(
            callback_url,
            headers=headers,
            json={"status": "ready", "frames": frames},
            timeout=120.0,
        ).raise_for_status()
    except Exception:
        httpx.post(
            callback_url,
            headers=headers,
            json={"status": "error", "error_message": "siglip failed", "frames": []},
            timeout=30.0,
        )


CLAP_NAME = "laion/larger_clap_general"

clap_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "torch>=2.4.0",
        "transformers>=4.49.0",
        "numpy>=1.26.0",
        "httpx>=0.27.0",
    )
    .env({"HF_XET_HIGH_PERFORMANCE": "1"})
)


@app.function(
    image=clap_image,
    gpu="L4",
    timeout=60 * MINUTES,
    scaledown_window=2 * MINUTES,
    volumes={"/root/.cache/huggingface": hf_cache_vol},
)
def embed_audio(
    video_id: str,
    chunks_url: str,
    callback_url: str,
    secret: str,
    clap_model: str = CLAP_NAME,
) -> None:
    import io
    import json
    import tarfile
    import wave
    from pathlib import Path
    from tempfile import TemporaryDirectory

    import httpx
    import numpy as np
    import torch
    from transformers import ClapModel, ClapProcessor

    del video_id
    headers = {"Authorization": f"Bearer {secret}"}
    tar_bytes = httpx.get(chunks_url, headers=headers, timeout=300.0).content
    chunks: list[dict] = []
    try:
        with TemporaryDirectory(prefix="ingest-clap-") as tmp:
            tar_path = Path(tmp) / "chunks.tar"
            tar_path.write_bytes(tar_bytes)
            extract_dir = Path(tmp) / "chunks"
            extract_dir.mkdir()
            with tarfile.open(tar_path, "r") as tar:
                tar.extractall(extract_dir, filter="data")
            manifest_path = extract_dir / "manifest.json"
            if manifest_path.is_file():
                items = json.loads(manifest_path.read_text(encoding="utf-8"))
            else:
                files = sorted(extract_dir.glob("chunk_*.wav"))
                items = [
                    {
                        "file": path.name,
                        "start_s": float(index) * 1.5,
                        "end_s": float(index) * 1.5 + 3.0,
                    }
                    for index, path in enumerate(files)
                ]
            model = ClapModel.from_pretrained(clap_model).eval()
            processor = ClapProcessor.from_pretrained(clap_model)
            for item in items:
                wav_path = extract_dir / item["file"]
                if not wav_path.is_file():
                    continue
                with wave.open(io.BytesIO(wav_path.read_bytes()), "rb") as handle:
                    n_frames = handle.getnframes()
                    rate = handle.getframerate()
                    raw = handle.readframes(n_frames)
                    width = handle.getsampwidth()
                if width != 2:
                    continue
                samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                inputs = processor(
                    audios=[samples],
                    sampling_rate=rate,
                    return_tensors="pt",
                    padding=True,
                )
                with torch.no_grad():
                    vector = model.get_audio_features(**inputs)
                    vector = vector / vector.norm(p=2, dim=-1, keepdim=True)
                chunks.append(
                    {
                        "start_s": float(item["start_s"]),
                        "end_s": float(item["end_s"]),
                        "embedding": [float(x) for x in vector[0].tolist()],
                    }
                )
        httpx.post(
            callback_url,
            headers=headers,
            json={"status": "ready", "chunks": chunks},
            timeout=120.0,
        ).raise_for_status()
    except Exception:
        httpx.post(
            callback_url,
            headers=headers,
            json={"status": "error", "error_message": "clap failed", "chunks": []},
            timeout=30.0,
        )


COLQWEN_NAME = "vidore/colqwen2.5-v0.2"

colqwen_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "torch>=2.4.0",
        "transformers>=4.49.0",
        "pillow>=10.0.0",
        "colpali-engine>=0.3.0",
        "httpx>=0.27.0",
    )
    .env({"HF_XET_HIGH_PERFORMANCE": "1"})
)


@app.function(
    image=colqwen_image,
    gpu="L4",
    timeout=60 * MINUTES,
    scaledown_window=2 * MINUTES,
    volumes={"/root/.cache/huggingface": hf_cache_vol},
)
def embed_slides(
    video_id: str,
    slides_url: str,
    callback_url: str,
    secret: str,
    colqwen_model: str = COLQWEN_NAME,
) -> None:
    import io
    import json
    import tarfile
    from pathlib import Path
    from tempfile import TemporaryDirectory

    import httpx
    import torch
    from PIL import Image

    del video_id
    headers = {"Authorization": f"Bearer {secret}"}
    tar_bytes = httpx.get(slides_url, headers=headers, timeout=300.0).content
    slides: list[dict] = []
    try:
        name = (colqwen_model or "").lower()
        if "2.5" in name or "2_5" in name:
            from colpali_engine.models import ColQwen2_5, ColQwen2_5_Processor

            model = ColQwen2_5.from_pretrained(colqwen_model).eval()
            processor = ColQwen2_5_Processor.from_pretrained(colqwen_model)
        else:
            from colpali_engine.models import ColQwen2, ColQwen2Processor

            model = ColQwen2.from_pretrained(colqwen_model).eval()
            processor = ColQwen2Processor.from_pretrained(colqwen_model)
        with TemporaryDirectory(prefix="ingest-colqwen-") as tmp:
            tar_path = Path(tmp) / "slides.tar"
            tar_path.write_bytes(tar_bytes)
            extract_dir = Path(tmp) / "slides"
            extract_dir.mkdir()
            with tarfile.open(tar_path, "r") as tar:
                tar.extractall(extract_dir, filter="data")
            manifest_path = extract_dir / "manifest.json"
            if manifest_path.is_file():
                items = json.loads(manifest_path.read_text(encoding="utf-8"))
            else:
                files = sorted(extract_dir.glob("slide_*.jpg"))
                items = [
                    {
                        "file": path.name,
                        "t_start_s": float(index),
                        "t_end_s": float(index) + 1.0,
                    }
                    for index, path in enumerate(files)
                ]
            for item in items:
                jpeg_path = extract_dir / item["file"]
                if not jpeg_path.is_file():
                    continue
                image = Image.open(io.BytesIO(jpeg_path.read_bytes())).convert("RGB")
                batch = processor.process_images([image])
                with torch.no_grad():
                    matrix = model(**batch)
                patches = [
                    [float(x) for x in token.tolist()] for token in matrix[0]
                ]
                slides.append(
                    {
                        "t_start_s": float(item["t_start_s"]),
                        "t_end_s": float(item["t_end_s"]),
                        "embeddings": patches,
                    }
                )
        httpx.post(
            callback_url,
            headers=headers,
            json={"status": "ready", "slides": slides},
            timeout=120.0,
        ).raise_for_status()
    except Exception:
        httpx.post(
            callback_url,
            headers=headers,
            json={"status": "error", "error_message": "colqwen failed", "slides": []},
            timeout=30.0,
        )
