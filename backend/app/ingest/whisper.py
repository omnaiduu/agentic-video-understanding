"""Whisper seam. Default laptop path is FakeWhisper; turbo runs on Modal."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TranscriptSegment:
    start_s: float
    end_s: float
    text: str


def transcribe_wav(wav_path: Path, model_name: str = "turbo") -> list[TranscriptSegment]:
    """Default: empty transcript (tests / INGEST=fake). Do not import faster-whisper here.

    Modal's ingest worker calls faster-whisper turbo and POSTs segments back.
    Tests monkeypatch this function to count calls and plant lines.
    """
    del wav_path, model_name
    return []
