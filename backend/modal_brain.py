"""Modal chat worker: vLLM OpenAI server, Gemma 4 E4B, L4, scale to zero.

Laptop FastAPI owns the JSON loop and only sends already-cut slices.
This process never sees the original video file. No tools= / tool-call parser.

Deploy from backend/:

    modal deploy modal_brain.py

Set BRAIN=vllm and VLLM_BASE_URL to the printed URL plus /v1.
Gemma 4 is gated: `modal secret create huggingface HUGGING_FACE_HUB_TOKEN=...`
"""

from __future__ import annotations

import json
import subprocess

import modal

MODEL_NAME = "google/gemma-4-E4B-it"
VLLM_PORT = 8000
MINUTES = 60

vllm_image = (
    modal.Image.from_registry("nvidia/cuda:12.8.0-devel-ubuntu22.04", add_python="3.12")
    .entrypoint([])
    .uv_pip_install("vllm[audio]==0.21.0")
    .env({"HF_XET_HIGH_PERFORMANCE": "1"})
)

hf_cache_vol = modal.Volume.from_name("huggingface-cache", create_if_missing=True)
vllm_cache_vol = modal.Volume.from_name("vllm-cache", create_if_missing=True)

app = modal.App("agentic-video-brain")


@app.server(
    image=vllm_image,
    gpu="L4",
    scaledown_window=2 * MINUTES,
    startup_timeout=10 * MINUTES,
    volumes={
        "/root/.cache/huggingface": hf_cache_vol,
        "/root/.cache/vllm": vllm_cache_vol,
    },
    port=VLLM_PORT,
    target_concurrency=8,
    secrets=[modal.Secret.from_name("huggingface")],
)
class Server:
    @modal.enter()
    def start(self) -> None:
        cmd = [
            "vllm",
            "serve",
            MODEL_NAME,
            "--served-model-name",
            MODEL_NAME,
            "--host",
            "0.0.0.0",
            "--port",
            str(VLLM_PORT),
            "--enforce-eager",
            "--max-model-len",
            "8192",
            "--gpu-memory-utilization",
            "0.90",
            "--limit-mm-per-prompt",
            json.dumps({"image": 64, "video": 0, "audio": 1}),
        ]
        self.process = subprocess.Popen(cmd)

    @modal.exit()
    def stop(self) -> None:
        self.process.terminate()
