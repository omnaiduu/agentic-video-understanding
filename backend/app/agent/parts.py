"""Turn Phase 2 bytes into OpenAI-style user content parts. Not tool messages."""

from __future__ import annotations

import base64
from typing import Any

from app.tools.frames import Frame

AUDIO_DROPPED_NOTE = (
    "Previous audio bytes were dropped (at most one audio per prompt). "
    "You already heard that window; do not require it again."
)


def jpeg_part(jpeg: bytes) -> dict:
    encoded = base64.b64encode(jpeg).decode("ascii")
    return {
        "type": "image_url",
        "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
    }


def wav_part(wav: bytes) -> dict:
    encoded = base64.b64encode(wav).decode("ascii")
    return {
        "type": "input_audio",
        "input_audio": {"data": encoded, "format": "wav"},
    }


def look_message(frames: list[Frame]) -> dict:
    labels = ", ".join(f"{frame.t:.2f}s" for frame in frames)
    text = f"frames at {labels}. Image parts on this user turn, not a tool result."
    content: list[dict] = [{"type": "text", "text": text}]
    content.extend(jpeg_part(frame.jpeg) for frame in frames)
    return {"role": "user", "content": content}


def strip_input_audio(messages: list[dict[str, Any]]) -> int:
    """Gemma/vLLM allows at most one input_audio per prompt."""
    removed = 0
    for msg in messages:
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        kept: list[Any] = []
        dropped = False
        for part in content:
            if isinstance(part, dict) and part.get("type") == "input_audio":
                dropped = True
                removed += 1
                continue
            kept.append(part)
        if dropped:
            texts = [
                part.get("text")
                for part in kept
                if isinstance(part, dict) and part.get("type") == "text"
            ]
            if not any(AUDIO_DROPPED_NOTE in (text or "") for text in texts):
                kept.append({"type": "text", "text": AUDIO_DROPPED_NOTE})
            msg["content"] = kept
    return removed


def listen_message(start_s: float, end_s: float, wav: bytes) -> dict:
    text = (
        f"audio from {start_s:.2f}s to {end_s:.2f}s. "
        "Audio part on this user turn, not a tool result."
    )
    return {
        "role": "user",
        "content": [
            {"type": "text", "text": text},
            wav_part(wav),
        ],
    }


def refuse_message(detail: str) -> dict:
    return {
        "role": "user",
        "content": (
            f"that cut was refused: {detail}. "
            "Try a smaller window. Do not dump the whole file."
        ),
    }


SPEECH_ONLY_NUDGE = (
    "These lines are only what was said out loud. "
    "If they do not answer the question, do a different move: "
    "look, listen, search_visual, search_audio, or search_slides. "
    "Do not search spoken words again. Do not only apologize."
)


def search_message(hits: list, query: str) -> dict:
    if not hits:
        text = (
            f"search for {query!r} returned no transcript hits. "
            "The whole talk is not attached. "
            f"{SPEECH_ONLY_NUDGE}"
        )
    else:
        lines = [f"[{hit.t:.1f}s] {hit.text}" for hit in hits]
        text = (
            f"transcript hits for {query!r} (at most 8, not the whole file):\n"
            + "\n".join(lines)
            + f"\n{SPEECH_ONLY_NUDGE}"
        )
    return {"role": "user", "content": text}


LOOK_THEN_ANSWER = (
    "Look at a short window under 2 seconds (fps 1 or omit fps), then answer. "
    "Do not only apologize. Do not invent a full index."
)


def speech_already_searched_message() -> dict:
    return {
        "role": "user",
        "content": (
            "You already searched what was said. Do not search spoken words again. "
            "If those lines do not answer, look, listen, search_visual, "
            "search_audio, or search_slides, then answer."
        ),
    }


def transcript_not_ready_message(status: str) -> dict:
    return {
        "role": "user",
        "content": (
            f"transcript is not ready (status={status}). "
            "No search results. Timed look and listen still work. "
            f"{LOOK_THEN_ANSWER} "
            "Do not invent a full transcript."
        ),
    }


def visual_search_message(hits: list, query: str) -> dict:
    if not hits:
        text = (
            f"search_visual for {query!r} returned no picture hits. "
            "Two hours of photos are not attached. Try another query or look."
        )
    else:
        lines = [f"[{hit.t:.1f}s] score={hit.score:.3f}" for hit in hits]
        text = (
            f"picture hits for {query!r} (at most 8 times, not the whole file; "
            "scores are not the answer; look to see):\n" + "\n".join(lines)
        )
    return {"role": "user", "content": text}


def visual_not_ready_message(status: str) -> dict:
    return {
        "role": "user",
        "content": (
            f"picture index is not ready (status={status}). "
            "No search_visual results. Timed look still works. "
            f"{LOOK_THEN_ANSWER} "
            "Do not invent a full photo log."
        ),
    }


def audio_search_message(result, query: str) -> dict:
    hits = getattr(result, "hits", result)
    if not hits:
        text = (
            f"search_audio for {query!r} returned no sound hits. "
            "Two hours of audio are not attached. Try another query or listen."
        )
    else:
        lines = [
            f"[{hit.start_s:.1f}s–{hit.end_s:.1f}s] score={hit.score:.3f}"
            for hit in hits
        ]
        text = (
            f"sound hits for {query!r} (at most 8 windows, not the whole file). "
            "These are times to listen, not a count of how many times a sound happened. "
            "Scores are not the answer; listen at a hit to hear:\n"
            + "\n".join(lines)
        )
    return {"role": "user", "content": text}


def export_message(kind: str, start_s: float, end_s: float, url: str) -> dict:
    label = "clip (mp4)" if kind == "clip" else "audio (wav)"
    return {
        "role": "user",
        "content": (
            f"exported {label} from {start_s:.2f}s to {end_s:.2f}s. "
            f"URL for the human: {url}. "
            "The cut file is not attached to this message and you do not get the bytes. "
            "Put this URL in your answer if the user asked for a file."
        ),
    }


def audio_not_ready_message(status: str) -> dict:
    return {
        "role": "user",
        "content": (
            f"sound index is not ready (status={status}). "
            "No search_audio results. Timed listen still works. "
            "Listen at a short window, then answer. Do not only apologize. "
            "Do not invent a full sound log."
        ),
    }


def slide_search_message(hits: list, query: str) -> dict:
    if not hits:
        text = (
            f"search_slides for {query!r} returned no slide hits. "
            "Two hours of frames are not attached. Try another query or look."
        )
    else:
        lines = [
            f"[{hit.t:.1f}s] score={hit.score:.3f} slide_id={hit.slide_id}"
            for hit in hits
        ]
        text = (
            f"slide hits for {query!r} (at most 8 times, not the whole file; "
            "scores are not the answer; look at the top hit under 2 seconds, then answer; "
            "describe the pixels — do not copy text from the question onto the wrong slide):\n"
            + "\n".join(lines)
        )
    return {"role": "user", "content": text}


def slides_not_ready_message(status: str) -> dict:
    return {
        "role": "user",
        "content": (
            f"slide index is not ready (status={status}). "
            "No search_slides results. Timed look still works. "
            f"{LOOK_THEN_ANSWER} "
            "Do not invent a full slide log."
        ),
    }
