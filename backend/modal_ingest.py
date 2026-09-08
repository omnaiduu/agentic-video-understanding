"""Modal ingest worker: faster-whisper turbo on L4. Not the chat GPU.

Laptop extracts the full audio track (no 30s listen cap) and serves it at
GET /internal/videos/{id}/audio. This worker transcribes, embeds passages,
and POSTs lines to POST /internal/videos/{id}/transcript. It never opens
laptop Postgres.

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
