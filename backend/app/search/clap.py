"""LAION-CLAP sound embedder. Tests and default laptop runs use FakeAudioEmbedder."""

from __future__ import annotations

import hashlib
import math
from functools import lru_cache
from typing import Protocol

from fastapi import Depends

from app.settings import Settings, get_settings

AUDIO_DIM = 512


class AudioEmbedder(Protocol):
    def embed_query(self, text: str) -> list[float]:
        """Dense vector for a search phrase (text tower)."""

    def embed_wavs(self, wavs: list[bytes]) -> list[list[float]]:
        """Dense vectors for index wav chunks (audio tower)."""


def hash_audio(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    while len(values) < AUDIO_DIM:
        digest = hashlib.sha256(digest).digest()
        values.extend(b - 128.0 for b in digest)
    values = values[:AUDIO_DIM]
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


class FakeAudioEmbedder:
    """No GPU. Optional query_vectors let tests plant a neighbor (chirp / clap)."""

    def __init__(self, query_vectors: dict[str, list[float]] | None = None) -> None:
        self.query_vectors = query_vectors or {}

    def embed_query(self, text: str) -> list[float]:
        planted = self.query_vectors.get(text)
        if planted is not None:
            return list(planted)
        return hash_audio("query:" + text)

    def embed_wavs(self, wavs: list[bytes]) -> list[list[float]]:
        return [hash_audio("wav:" + hashlib.sha256(blob).hexdigest()) for blob in wavs]


class ClapEmbedder:
    """laion/larger_clap_general (or another name in config). Optional extra."""

    def __init__(self, model_name: str) -> None:
        from transformers import ClapModel, ClapProcessor

        self._model = ClapModel.from_pretrained(model_name).eval()
        self._processor = ClapProcessor.from_pretrained(model_name)

    def embed_query(self, text: str) -> list[float]:
        import torch

        inputs = self._processor(text=[text], return_tensors="pt", padding=True)
        with torch.no_grad():
            vector = self._model.get_text_features(**inputs)
            vector = vector / vector.norm(p=2, dim=-1, keepdim=True)
        return [float(x) for x in vector[0].tolist()]

    def embed_wavs(self, wavs: list[bytes]) -> list[list[float]]:
        if not wavs:
            return []
        import io
        import wave

        import numpy as np
        import torch

        arrays: list = []
        rates: list[int] = []
        for blob in wavs:
            with wave.open(io.BytesIO(blob), "rb") as handle:
                n_frames = handle.getnframes()
                sample_width = handle.getsampwidth()
                rate = handle.getframerate()
                raw = handle.readframes(n_frames)
            if sample_width != 2:
                raise ValueError("CLAP ingest wavs must be 16-bit PCM")
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            arrays.append(samples)
            rates.append(rate)
        sampling_rate = rates[0] if rates else 48000
        inputs = self._processor(
            audios=arrays, sampling_rate=sampling_rate, return_tensors="pt", padding=True
        )
        with torch.no_grad():
            matrix = self._model.get_audio_features(**inputs)
            matrix = matrix / matrix.norm(p=2, dim=-1, keepdim=True)
        return [[float(x) for x in row.tolist()] for row in matrix]


@lru_cache
def _clap(model_name: str) -> ClapEmbedder:
    return ClapEmbedder(model_name)


def build_audio_embedder(settings: Settings | None = None) -> AudioEmbedder:
    cfg = settings or get_settings()
    if cfg.audio_embedder == "clap":
        return _clap(cfg.clap_model)
    if cfg.audio_embedder == "fake":
        return FakeAudioEmbedder()
    raise RuntimeError(f"unknown AUDIO_EMBEDDER={cfg.audio_embedder}")


def get_audio_embedder(settings: Settings = Depends(get_settings)) -> AudioEmbedder:
    return build_audio_embedder(settings)
