#!/usr/bin/env python3
"""Live hidden-intent A/B runner. Same eight questions E4B already ran.

Does not deploy a model. Point BASE_URL at FastAPI; FastAPI points at whatever
brain VLLM_MODEL / VLLM_BASE_URL is set to (E4B today, 12B later).

    cd backend
    VIDEO_ID=... BASE_URL=http://127.0.0.1:8000 BRAIN_LABEL=e4b \\
      uv run python eval/run_hidden_intent_suite.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import httpx

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from eval.hidden_intent import E4B_OBSERVATIONS, QUESTIONS  # noqa: E402


def summarize(body: dict) -> dict:
    steps = body.get("steps") or []
    return {
        "http": body.get("_http"),
        "answer": (body.get("answer") or "")[:1200],
        "export_url": body.get("export_url"),
        "citations": body.get("citations"),
        "steps": [
            {
                "do": s.get("do"),
                "ok": s.get("ok"),
                "start_s": s.get("start_s"),
                "end_s": s.get("end_s"),
                "detail": (s.get("detail") or "")[:240],
            }
            for s in steps
        ],
        "error": body.get("detail") or body.get("error"),
    }


def listened_before_export(steps: list[dict]) -> bool:
    seen_listen = False
    for step in steps:
        if step.get("do") == "listen" and step.get("ok"):
            seen_listen = True
        if step.get("do") in ("export_clip", "export_audio") and step.get("ok"):
            return seen_listen
    return False


def searched_speech(steps: list[dict]) -> bool:
    return any(step.get("do") == "search" and step.get("ok") for step in steps)


def main() -> None:
    video_id = os.environ.get("VIDEO_ID", "").strip()
    if not video_id:
        raise SystemExit("Set VIDEO_ID to an uploaded tape id.")
    base = os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    label = os.environ.get("BRAIN_LABEL", "unknown")
    out = Path(os.environ.get("OUT", f"/tmp/hidden-intent-{label}.json"))
    results: dict = {
        "brain_label": label,
        "video_id": video_id,
        "base_url": base,
        "questions": {},
    }
    with httpx.Client(timeout=httpx.Timeout(600.0, connect=30.0)) as client:
        for qid, question in QUESTIONS:
            print(f"\n=== {qid} ({label}) ===", flush=True)
            t0 = time.time()
            try:
                response = client.post(
                    f"{base}/videos/{video_id}/chat",
                    json={"message": question},
                )
            except Exception as exc:
                results["questions"][qid] = {
                    "question": question,
                    "http": None,
                    "error": str(exc),
                    "elapsed_s": round(time.time() - t0, 1),
                    "e4b_note": E4B_OBSERVATIONS.get(qid),
                }
                print("EXC", exc, flush=True)
                continue
            elapsed = round(time.time() - t0, 1)
            try:
                body = response.json()
            except Exception:
                body = {"raw": response.text[:2000]}
            if isinstance(body, dict):
                body["_http"] = response.status_code
            summary = summarize(body) if isinstance(body, dict) else {"raw": body}
            summary["question"] = question
            summary["elapsed_s"] = elapsed
            summary["http"] = response.status_code
            summary["listened_before_export"] = listened_before_export(
                summary.get("steps") or []
            )
            summary["searched_speech"] = searched_speech(summary.get("steps") or [])
            summary["e4b_note"] = E4B_OBSERVATIONS.get(qid)
            results["questions"][qid] = summary
            print(f"http={response.status_code} t={elapsed}s", flush=True)
            print((summary.get("answer") or summary.get("error") or "")[:400], flush=True)
            print(
                "steps:",
                [
                    (s["do"], s["ok"], s.get("start_s"), s.get("end_s"))
                    for s in summary.get("steps") or []
                ],
                flush=True,
            )
            print(
                "listen_before_export=",
                summary["listened_before_export"],
                "searched_speech=",
                summary["searched_speech"],
                flush=True,
            )
            out.write_text(json.dumps(results, indent=2))
    print("\nWrote", out, flush=True)


if __name__ == "__main__":
    main()
