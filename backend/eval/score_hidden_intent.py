#!/usr/bin/env python3
"""Score a hidden-intent suite JSON. Steps and wording, not loop bounces.

Does not hardcode beep→11s into the laptop loop. This file only grades the
A/B traces for the exam tape after the fact.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from eval.hidden_intent import QUESTIONS, question_ids  # noqa: E402

WINDOW_TOL_S = 0.75
_EXPORTS = frozenset({"export_clip", "export_audio"})


def _window(step: dict) -> tuple[float, float] | None:
    start = step.get("start_s")
    end = step.get("end_s")
    if start is None or end is None:
        return None
    return (float(start), float(end))


def _close(
    left: tuple[float, float],
    right: tuple[float, float],
    tol: float = WINDOW_TOL_S,
) -> bool:
    return abs(left[0] - right[0]) <= tol and abs(left[1] - right[1]) <= tol


def _first_ok(steps: list[dict], *dos: str) -> dict | None:
    wanted = frozenset(dos)
    for step in steps:
        if step.get("do") in wanted and step.get("ok"):
            return step
    return None


def _ok_steps(body: dict) -> list[dict]:
    return list(body.get("steps") or [])


def _answer(body: dict) -> str:
    return str(body.get("answer") or "")


def _http_ok(body: dict) -> bool:
    return body.get("http") == 200


def listened_before_export(steps: list[dict]) -> bool:
    seen_listen = False
    for step in steps:
        if step.get("do") == "listen" and step.get("ok"):
            seen_listen = True
        if step.get("do") in _EXPORTS and step.get("ok"):
            return seen_listen
    return False


def searched_speech(steps: list[dict]) -> bool:
    return any(step.get("do") == "search" and step.get("ok") for step in steps)


def looked(steps: list[dict]) -> bool:
    return any(step.get("do") == "look" and step.get("ok") for step in steps)


def exported(steps: list[dict]) -> bool:
    return any(step.get("do") in _EXPORTS and step.get("ok") for step in steps)


def exported_heard_range(steps: list[dict]) -> bool:
    """True if the first successful export matches a listen window already heard."""
    listens: list[tuple[float, float]] = []
    for step in steps:
        if step.get("do") == "listen" and step.get("ok"):
            window = _window(step)
            if window is not None:
                listens.append(window)
        if step.get("do") in _EXPORTS and step.get("ok"):
            export = _window(step)
            if export is None or not listens:
                return False
            return any(_close(export, heard) for heard in listens)
    return False


def dumped_unheard_clap_window(steps: list[dict]) -> bool:
    """Export matches the first CLAP hit and that cut was never listened to."""
    hit = _first_ok(steps, "search_audio")
    export = _first_ok(steps, *_EXPORTS)
    if hit is None or export is None:
        return False
    hit_w = _window(hit)
    export_w = _window(export)
    if hit_w is None or export_w is None:
        return False
    if not _close(hit_w, export_w):
        return False
    return not exported_heard_range(steps)


def _has(text: str, *needles: str) -> bool:
    lower = text.lower()
    return any(needle.lower() in lower for needle in needles)


def _leads_with_yes(text: str) -> bool:
    stripped = text.strip().lower()
    return stripped.startswith("yes")


def _positive_clap_count(text: str) -> bool:
    lower = text.lower()
    if re.search(r"\b(zero|no|none|0)\b.{0,24}clap", lower):
        return False
    if re.search(r"clap.{0,24}\b(zero|none|0)\b", lower):
        return False
    return bool(
        re.search(
            r"\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\b.{0,20}clap",
            lower,
        )
        or re.search(
            r"clap.{0,20}\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\b",
            lower,
        )
    )


def _zero_claps(text: str) -> bool:
    lower = text.lower()
    return bool(
        re.search(r"\b(zero|0)\b.{0,24}clap", lower)
        or re.search(r"no clap", lower)
        or "aren't any clap" in lower
        or "are not any clap" in lower
        or "there are no clap" in lower
        or "didn't hear a clap" in lower
        or "did not hear a clap" in lower
        or "did not hear any clap" in lower
        or "didn't hear any clap" in lower
    )


def score_question(qid: str, body: dict) -> dict[str, Any]:
    steps = _ok_steps(body)
    answer = _answer(body)
    flags = {
        "http_ok": _http_ok(body),
        "listened_before_export": listened_before_export(steps),
        "exported_heard_range": exported_heard_range(steps),
        "dumped_unheard_clap_window": dumped_unheard_clap_window(steps),
        "searched_speech": searched_speech(steps),
        "looked": looked(steps),
        "exported": exported(steps),
    }
    if "listened_before_export" in body:
        flags["listened_before_export"] = bool(body["listened_before_export"])
    if "searched_speech" in body:
        flags["searched_speech"] = bool(body["searched_speech"])

    verdict = "fail"
    reason = "HTTP was not 200."
    if flags["http_ok"]:
        verdict, reason = _verdict_for(qid, answer, flags, steps)

    return {
        "qid": qid,
        "verdict": verdict,
        "reason": reason,
        "flags": flags,
        "answer": answer[:400],
        "steps": [
            (s.get("do"), s.get("ok"), s.get("start_s"), s.get("end_s"))
            for s in steps
        ],
    }


def _verdict_for(
    qid: str, answer: str, flags: dict[str, bool], steps: list[dict]
) -> tuple[str, str]:
    if qid == "E1":
        if _has(answer, "$99", "99"):
            return "pass", "HTTP 200 and names $99."
        return "fail", "HTTP 200 but the answer does not name $99."

    if qid == "H1":
        rejects = _has(
            answer,
            "not on red",
            "isn't on red",
            "is not on the red",
            "not on the red",
            "navy",
            "dark blue",
            "pricing",
        )
        if _leads_with_yes(answer) and not rejects:
            return "fail", "Leads with Yes on the false premise."
        if rejects:
            return "pass", "Rejects the false premise from the pixels."
        return "partial", "HTTP 200 but does not clearly say the price is not on red."

    if qid == "M3":
        if _has(answer, "ship"):
            return "pass", "HTTP 200 and names what to ship."
        return "fail", "HTTP 200 but does not name the printed ship line."

    if qid == "M4":
        had_audio = any(s.get("do") == "search_audio" and s.get("ok") for s in steps)
        heard = any(s.get("do") == "listen" and s.get("ok") for s in steps)
        if not had_audio:
            return "fail", "Never opened the sound book."
        if not (heard or flags["looked"]):
            return "fail", "Did not look/listen inside a sound hit."
        if _has(answer, "q3", "ship", "roadmap"):
            return "pass", "Opened sound, then looked/listened, and named the screen."
        return "partial", "Looked or listened after sound search but did not name the slide."

    if qid == "M1":
        if not flags["searched_speech"]:
            return "fail", "Answered without searching spoken words."
        if not flags["looked"]:
            return "fail", "Searched speech but never looked at the printed number."
        color = _has(answer, "yellow", "gold", "orange")
        match = _has(answer, "match", "same", "yes")
        if color and match:
            return "pass", "Looked and searched speech; names a color and match/no-match."
        if color:
            return "partial", "Opened both books and named a color, but no clear match sentence."
        return "partial", "Opened both books, but did not name the printed color."

    if qid == "H5":
        heard = any(s.get("do") == "listen" and s.get("ok") for s in steps)
        if not heard:
            return "fail", "Did not listen before counting."
        if _positive_clap_count(answer) and not _zero_claps(answer):
            return "fail", "Invented a clap count after a listen."
        if _zero_claps(answer):
            return "pass", "Listened and said zero / no claps."
        return "partial", "Listened and did not invent a count, but did not say zero."

    if qid == "H7":
        if not flags["exported"]:
            return "fail", "Asked for a clip but never exported."
        if not flags["listened_before_export"]:
            return "fail", "Exported without listening first."
        if flags["dumped_unheard_clap_window"]:
            return "fail", "Exported the raw CLAP window without hearing that range."
        if flags["exported_heard_range"]:
            return "pass", "Listened, then exported the range it heard."
        return "partial", "Listened before export, but the cut does not match a heard window."

    if qid == "H8":
        names = (
            _has(answer, "pricing")
            and _has(answer, "red alert", "redalert", "red-alert")
            and _has(answer, "q3", "ship")
        )
        if names:
            return "pass", "Walk names Pricing, RED ALERT, and Q3."
        missing = []
        if not _has(answer, "pricing"):
            missing.append("Pricing")
        if not _has(answer, "red alert", "redalert", "red-alert"):
            missing.append("RED ALERT")
        if not _has(answer, "q3", "ship"):
            missing.append("Q3")
        return "fail", "Walk missed: " + ", ".join(missing) + "."

    return "fail", f"Unknown question id {qid}."


def score_run(payload: dict) -> dict[str, Any]:
    questions: dict[str, Any] = {}
    for qid, _text in QUESTIONS:
        body = (payload.get("questions") or {}).get(qid) or {}
        questions[qid] = score_question(qid, body)
    tallies = {"pass": 0, "partial": 0, "fail": 0}
    for row in questions.values():
        tallies[row["verdict"]] = tallies.get(row["verdict"], 0) + 1
    return {
        "brain_label": payload.get("brain_label"),
        "video_id": payload.get("video_id"),
        "vllm_model": payload.get("vllm_model"),
        "questions": questions,
        "tallies": tallies,
        "order": question_ids(),
    }


def markdown_table(scored: dict) -> str:
    lines = [
        f"Brain: `{scored.get('brain_label') or 'unknown'}`"
        + (f" (`{scored['vllm_model']}`)" if scored.get("vllm_model") else ""),
        "",
        "| Q | Verdict | Why |",
        "|---|---|---|",
    ]
    for qid in scored.get("order") or question_ids():
        row = scored["questions"][qid]
        reason = (row.get("reason") or "").replace("|", "/")
        lines.append(f"| **{qid}** | **{row['verdict']}** | {reason} |")
    tallies = scored.get("tallies") or {}
    lines.append("")
    lines.append(
        f"Tallies: pass={tallies.get('pass', 0)} "
        f"partial={tallies.get('partial', 0)} "
        f"fail={tallies.get('fail', 0)}."
    )
    return "\n".join(lines)


def compare_markdown(left: dict, right: dict, left_name: str, right_name: str) -> str:
    lines = [
        f"| Q | {left_name} | {right_name} | 12B looks better if… |",
        "|---|---|---|---|",
    ]
    hints = {
        "E1": "Must not regress on $99.",
        "H1": "Rejects the false premise; does not lead with Yes.",
        "M3": "Must not regress on ship.",
        "M4": "Listens inside the hit, then says what is on screen.",
        "M1": "`search` speech and a look; names color + match.",
        "H5": "Listens; does not invent claps; zero is allowed.",
        "H7": "`listen` before `export_clip`; cut is the heard range.",
        "H8": "Still names Pricing, RED ALERT, Q3.",
    }
    for qid in question_ids():
        l_row = left["questions"][qid]
        r_row = right["questions"][qid]
        lines.append(
            f"| **{qid}** | {l_row['verdict']} | {r_row['verdict']} | {hints[qid]} |"
        )
    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "Usage: score_hidden_intent.py RUN.json [OTHER.json]\n"
            "Writes a markdown table to stdout. Two files → A/B columns."
        )
    first = json.loads(Path(sys.argv[1]).read_text())
    scored = score_run(first)
    print(markdown_table(scored))
    out = Path(sys.argv[1]).with_suffix(".score.json")
    out.write_text(json.dumps(scored, indent=2))
    print(f"\nWrote {out}", flush=True)
    if len(sys.argv) >= 3:
        second = json.loads(Path(sys.argv[2]).read_text())
        other = score_run(second)
        print("\n" + markdown_table(other))
        print(
            "\n"
            + compare_markdown(
                scored,
                other,
                str(scored.get("brain_label") or "left"),
                str(other.get("brain_label") or "right"),
            )
        )


if __name__ == "__main__":
    main()
