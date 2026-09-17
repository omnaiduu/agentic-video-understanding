#!/usr/bin/env python3
"""Poll a vLLM OpenAI /v1/models URL until HTTP 200. Used after modal deploy."""

from __future__ import annotations

import os
import sys
import time
import urllib.error
import urllib.request


def wait_models(base_url: str, timeout_s: int = 1200) -> None:
    root = base_url.rstrip("/")
    url = root if root.endswith("/models") else f"{root}/models"
    deadline = time.time() + timeout_s
    last = "no-request"
    n = 0
    while time.time() < deadline:
        n += 1
        try:
            request = urllib.request.Request(
                url,
                headers={"Authorization": "Bearer EMPTY"},
                method="GET",
            )
            with urllib.request.urlopen(request, timeout=45) as response:
                code = response.status
                body = response.read()[:200]
                print(f"try {n} http:{code} {body!r}", flush=True)
                if code == 200:
                    return
                last = f"http {code}"
        except Exception as exc:
            last = str(exc)
            print(f"try {n} {last}", flush=True)
        time.sleep(15)
    raise SystemExit(f"vLLM not ready within {timeout_s}s ({last})")


def main() -> None:
    base = os.environ.get("VLLM_BASE_URL", "").strip()
    if not base:
        raise SystemExit("Set VLLM_BASE_URL to the worker /v1 URL.")
    timeout = int(os.environ.get("WAIT_S", "1200"))
    wait_models(base, timeout)
    print("READY", flush=True)


if __name__ == "__main__":
    sys.exit(main())
