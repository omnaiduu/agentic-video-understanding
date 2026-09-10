"""Modal chat worker: vLLM OpenAI server, Gemma 4 E4B, L4, scale to zero.

Laptop FastAPI owns the JSON loop and only sends already-cut slices.
This process never sees the original video file. No tools= / tool-call parser.

Idle containers shut down after 15 minutes. min_containers=0 so the GPU is
not kept warm. After the first cold start, CPU+GPU memory snapshots make
later boots faster.

Deploy from backend/:

    modal deploy modal_brain.py

Set BRAIN=vllm and VLLM_BASE_URL to the printed URL plus /v1.
Gemma 4 is gated: `modal secret create huggingface HUGGING_FACE_HUB_TOKEN=...`
"""

from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request

import modal

MODEL_NAME = "google/gemma-4-E4B-it"
VLLM_PORT = 8000
MINUTES = 60
IDLE_WINDOW = 15 * MINUTES
STARTUP_WAIT = 15 * MINUTES

vllm_image = (
    modal.Image.from_registry("nvidia/cuda:12.8.0-devel-ubuntu22.04", add_python="3.12")
    .entrypoint([])
    .uv_pip_install("vllm[audio]==0.29.0", "transformers>=5.5.0", "requests")
    .env(
        {
            "HF_HUB_CACHE": "/root/.cache/huggingface",
            "HF_XET_HIGH_PERFORMANCE": "1",
            "VLLM_SERVER_DEV_MODE": "1",
        }
    )
)

hf_cache_vol = modal.Volume.from_name("huggingface-cache", create_if_missing=True)
vllm_cache_vol = modal.Volume.from_name("vllm-cache", create_if_missing=True)
hf_secret = modal.Secret.from_name("huggingface")

app = modal.App("agentic-video-brain")


def _url(path: str) -> str:
    return f"http://127.0.0.1:{VLLM_PORT}{path}"


def _check_running(process: subprocess.Popen[bytes]) -> None:
    code = process.poll()
    if code is not None:
        raise subprocess.CalledProcessError(code, cmd=process.args)


def wait_ready(process: subprocess.Popen[bytes], timeout: int = STARTUP_WAIT) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        _check_running(process)
        try:
            urllib.request.urlopen(_url("/health"), timeout=3)
            return
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            time.sleep(3)
    raise TimeoutError(f"vLLM server not ready within {timeout} seconds")


def warmup() -> None:
    payload = json.dumps(
        {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 8,
        }
    ).encode()
    request = urllib.request.Request(
        _url("/v1/chat/completions"),
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(request, timeout=120)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return


def sleep(level: int = 1) -> None:
    request = urllib.request.Request(
        _url(f"/sleep?level={level}"),
        data=b"",
        method="POST",
    )
    urllib.request.urlopen(request, timeout=120)


def wake_up() -> None:
    request = urllib.request.Request(_url("/wake_up"), data=b"", method="POST")
    urllib.request.urlopen(request, timeout=120)


@app.server(
    image=vllm_image,
    gpu="L4",
    scaledown_window=IDLE_WINDOW,
    startup_timeout=STARTUP_WAIT,
    volumes={
        "/root/.cache/huggingface": hf_cache_vol,
        "/root/.cache/vllm": vllm_cache_vol,
    },
    port=VLLM_PORT,
    target_concurrency=8,
    min_containers=0,
    max_containers=1,
    secrets=[hf_secret],
    enable_memory_snapshot=True,
    experimental_options={"enable_gpu_snapshot": True},
    unauthenticated=True,
)
class Server:
    @modal.enter(snap=True)
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
            "--enable-sleep-mode",
            "--max-model-len",
            "8192",
            "--gpu-memory-utilization",
            "0.90",
            "--limit-mm-per-prompt",
            json.dumps({"image": 64, "video": 0, "audio": 1}),
        ]
        self.process = subprocess.Popen(cmd)
        wait_ready(self.process)
        warmup()
        sleep(level=1)

    @modal.enter(snap=False)
    def restore(self) -> None:
        wake_up()

    @modal.exit()
    def stop(self) -> None:
        process = getattr(self, "process", None)
        if process is not None:
            process.terminate()
