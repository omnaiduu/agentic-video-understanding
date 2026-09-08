"""Turn Phase 2 bytes into OpenAI-style user content parts. Not tool messages."""

from __future__ import annotations

import base64

from app.tools.frames import Frame


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


def search_message(hits: list, query: str) -> dict:
    if not hits:
        text = (
            f"search for {query!r} returned no transcript hits. "
            "The whole talk is not attached. Try another query, look, or listen."
        )
    else:
        lines = [f"[{hit.t:.1f}s] {hit.text}" for hit in hits]
        text = (
            f"transcript hits for {query!r} (at most 8, not the whole file):\n"
            + "\n".join(lines)
        )
    return {"role": "user", "content": text}


def transcript_not_ready_message(status: str) -> dict:
    return {
        "role": "user",
        "content": (
            f"transcript is not ready (status={status}). "
            "No search results. Timed look and listen still work. "
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
            "Do not invent a full photo log."
        ),
    }


def audio_search_message(result, query: str) -> dict:
    hits = getattr(result, "hits", result)
    clusters = getattr(result, "clusters", [])
    count = getattr(result, "count", len(clusters))
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
        cluster_lines = [
            f"{cluster.start_s:.1f}s–{cluster.end_s:.1f}s (n={cluster.n_hits})"
            for cluster in clusters
        ]
        merged = ", ".join(cluster_lines) if cluster_lines else "none"
        text = (
            f"sound hits for {query!r} (at most 8 windows, not the whole file; "
            "scores are not the answer; listen to hear):\n"
            + "\n".join(lines)
            + f"\nmerged events: count={count} via Python merge+len: {merged}"
        )
    return {"role": "user", "content": text}


def audio_not_ready_message(status: str) -> dict:
    return {
        "role": "user",
        "content": (
            f"sound index is not ready (status={status}). "
            "No search_audio results. Timed listen still works. "
            "Do not invent a full sound log."
        ),
    }
