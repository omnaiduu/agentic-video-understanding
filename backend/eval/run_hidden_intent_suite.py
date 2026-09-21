#!/usr/bin/env python3
"""Live hidden-intent A/B runner. Same eight questions E4B already ran.

Point BASE_URL at FastAPI; FastAPI points at whatever brain VLLM_MODEL /
VLLM_BASE_URL is set to (E4B default, 12B for this A/B). Do not deploy from
this script. THINKING=1 posts ChatIn.thinking=true (E4B thinking worker).

    cd backend
    VIDEO_ID=... BASE_URL=http://127.0.0.1:8000 BRAIN_LABEL=e4b \\
      uv run python eval/run_hidden_intent_suite.py

    THINKING=1 BRAIN_LABEL=e4b-thinking OUT=/tmp/hidden-intent-e4b-thinking.json \\
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

from eval.brains import EXAM_TAPE_ID  # noqa: E402
from eval.hidden_intent import E4B_OBSERVATIONS, QUESTIONS  # noqa: E402
from eval.score_hidden_intent import (  # noqa: E402
    dumped_unheard_clap_window,
    exported_heard_range,
    listened_before_export,
    markdown_table,
    score_run,
    searched_speech,
)


def summarize(body: dict) -> dict:
    steps = body.get("steps") or []
    return {
        "http": body.get("_http"),
        "answer": (body.get("answer") or "")[:1200],
        "export_url": body.get("export_url"),
        "citations": body.get("citations"),
        "thinking": body.get("thinking"),
        "thoughts": body.get("thoughts") or [],
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


def main() -> None:
    video_id = os.environ.get("VIDEO_ID", "").strip() or EXAM_TAPE_ID
    base = os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    label = os.environ.get("BRAIN_LABEL", "unknown")
    model = os.environ.get("VLLM_MODEL", "")
    thinking = os.environ.get("THINKING", "").strip().lower() in {"1", "true", "yes"}
    out = Path(os.environ.get("OUT", f"/tmp/hidden-intent-{label}.json"))
    results: dict = {
        "brain_label": label,
        "vllm_model": model,
        "thinking": thinking,
        "video_id": video_id,
        "base_url": base,
        "questions": {},
    }
    with httpx.Client(timeout=httpx.Timeout(600.0, connect=30.0)) as client:
        for qid, question in QUESTIONS:
            print(f"\n=== {qid} ({label}{' thinking' if thinking else ''}) ===", flush=True)
            t0 = time.time()
            payload = {"message": question}
            if thinking:
                payload["thinking"] = True
            try:
                response = client.post(
                    f"{base}/videos/{video_id}/chat",
                    json=payload,
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
            steps = summary.get("steps") or []
            summary["listened_before_export"] = listened_before_export(steps)
            summary["searched_speech"] = searched_speech(steps)
            summary["exported_heard_range"] = exported_heard_range(steps)
            summary["dumped_unheard_clap_window"] = dumped_unheard_clap_window(steps)
            summary["e4b_note"] = E4B_OBSERVATIONS.get(qid)
            results["questions"][qid] = summary
            print(f"http={response.status_code} t={elapsed}s", flush=True)
            print((summary.get("answer") or summary.get("error") or "")[:400], flush=True)
            print(
                "steps:",
                [
                    (s["do"], s["ok"], s.get("start_s"), s.get("end_s"))
                    for s in steps
                ],
                flush=True,
            )
            print(
                "listen_before_export=",
                summary["listened_before_export"],
                "exported_heard_range=",
                summary["exported_heard_range"],
                "dumped_unheard_clap=",
                summary["dumped_unheard_clap_window"],
                "searched_speech=",
                summary["searched_speech"],
                flush=True,
            )
            out.write_text(json.dumps(results, indent=2))
    scored = score_run(results)
    results["score"] = scored
    out.write_text(json.dumps(results, indent=2))
    print("\n" + markdown_table(scored), flush=True)
    print("\nWrote", out, flush=True)


if __name__ == "__main__":
    main()
