"""JSON form Gemma fills. vLLM constrains the shape; the prompt teaches meaning."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError


MAX_ROUNDS = 8
DoKind = Literal[
    "look",
    "listen",
    "search",
    "search_visual",
    "search_audio",
    "search_slides",
    "export_clip",
    "export_audio",
    "answer",
]


class BrainAction(BaseModel):
    do: DoKind
    start_s: float | None = None
    end_s: float | None = None
    fps: float | None = None
    query: str | None = None
    answer: str | None = None
    times: list[float] = Field(default_factory=list)


BRAIN_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "do": {
            "type": "string",
            "enum": [
                "look",
                "listen",
                "search",
                "search_visual",
                "search_audio",
                "search_slides",
                "export_clip",
                "export_audio",
                "answer",
            ],
        },
        "start_s": {"type": ["number", "null"]},
        "end_s": {"type": ["number", "null"]},
        "fps": {"type": ["number", "null"]},
        "query": {"type": ["string", "null"]},
        "answer": {"type": ["string", "null"]},
        "times": {"type": "array", "items": {"type": "number"}},
    },
    "required": ["do", "start_s", "end_s", "fps", "query", "answer", "times"],
    "additionalProperties": False,
}

RESPONSE_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "brain_action",
        "schema": BRAIN_JSON_SCHEMA,
        "strict": True,
    },
}

SYSTEM_PROMPT = """You fill a JSON form about one video. You do not call tools.

Moves:
- look: we cut JPEG frames from start_s to end_s (optional fps). Cap: seconds × fps ≤ 64 photos. Default fps is 1. Prefer windows under 2 seconds. Oversize is refused; pick a smaller window. We ignore answer.
- listen: we cut 16 kHz mono wav from start_s to end_s. Cap: 30 seconds. Oversize is refused. We ignore answer.
- search: we hybrid-search the Whisper transcript (keyword + meaning). Put the phrase in query, or null to use the user question. We return at most 8 {t, text} hits as text, never the whole talk. We ignore answer. Those hits are only spoken words. If they do not answer, look, listen, search_visual, search_audio, or search_slides — do not search spoken words again. Do not only apologize. If the transcript is not ready, we say so; look or listen, then answer.
- search_visual: we dense-search the SigLIP picture index. Put the phrase in query, or null to use the user question. We return at most 8 {t, score} hits as text, never two hours of photos. Scores are not the answer; look at a hit to see. We ignore answer. If the picture book is not ready, we say so; timed look still works — look, then answer.
- search_audio: we dense-search the CLAP sound index. Put the phrase in query, or null to use the user question. We return at most 8 {start, end, score} hits as text, never two hours of audio. Those times are places to listen, not a count of how many times a sound happened. Look, listen, or export near the middle of a window (under 2 seconds), not the start — the start can be a different moment. If you are asked how many times a sound happened, listen at a hit first; if you do not hear that sound, the count is zero. Scores are not the answer. We ignore answer. If the sound book is not ready, we say so; timed listen still works — listen, then answer.
- search_slides: we MaxSim-search unique slides (ColQwen2.x patches). Put the phrase in query, or null to use the user question. We return at most 8 {t, score, slide_id} hits as text, never two hours of frames. Scores are not the answer; look at a hit to read the real frame. We ignore answer. Search this book at most once, then look at the top hit (under 2 seconds). After look, describe the pixels. If that frame does not answer, look at the next unused time on the list (still under 2 seconds) — do not look at a time you already looked at, do not copy a price from the question onto the wrong slide. If the slide book is not ready, we say so; timed look still works — look, then answer. Do not use this for birds or red lights (that is search_visual) or spoken words (that is search).
- export_clip: we re-encode an mp4 from start_s to end_s onto disk. Cap: 60 seconds. Oversize is refused; we do not shrink. Audio-only files cannot export_clip. We return a GET URL for the human. You do not get the clip bytes. We ignore answer.
- export_audio: we re-encode a wav from start_s to end_s onto disk. Cap: 60 seconds. Oversize is refused. We return a GET URL for the human. You do not get the wav bytes. We ignore answer.
- answer: you are done. Put the user-facing text in answer and citation timestamps (seconds) in times. If we exported, include the URL.

Follow-ups: if last time windows are listed, use them first for "that" / "there" / "the clip" / "that frame". You may look or listen again at those times. Do not search the whole tape from scratch unless the new question needs a new find. Old photos and audio are not re-attached.

After look, listen, search, search_visual, search_audio, search_slides, export_clip, or export_audio we send the result as a normal user message, not as a tool result.

Do not refuse to describe what is on screen and what can be heard. Look at a few short windows in order, then answer. Include things not said out loud. Do not only apologize.

When we say you have no more moves, you must answer from what you already saw or heard.

Only look, listen, search, search_visual, search_audio, search_slides, export_clip, export_audio, and answer exist now. Return only the JSON object."""

RETRY_PROMPT = "Return only the JSON object that matches the schema. No markdown, no extra keys."

FORCE_ANSWER_PROMPT = (
    "You have no more look/listen/search/export moves. "
    "Answer now from what you already saw or heard. "
    "Trust frames and audio over the wording of the question. "
    "If a frame is red or a different heading, say that."
)


class BrainParseError(ValueError):
    """Model output was not valid BrainAction JSON."""


def parse_action(raw: str) -> BrainAction:
    text = (raw or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        inner = [line for line in lines if not line.startswith("```")]
        text = "\n".join(inner).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise BrainParseError("model did not return JSON") from exc
    try:
        return BrainAction.model_validate(payload)
    except ValidationError as exc:
        raise BrainParseError(
            "JSON did not match look/listen/search/search_visual/search_audio/search_slides/export/answer"
        ) from exc
