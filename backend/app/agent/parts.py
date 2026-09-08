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
