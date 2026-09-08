"""CLAP seam. Default laptop path is fake; real LAION-CLAP runs on Modal."""

from __future__ import annotations

from app.search.clap import AUDIO_DIM, FakeAudioEmbedder


def embed_wavs(wavs: list[bytes], model_name: str = "") -> list[list[float]]:
    """Default: hash vectors (tests / INGEST=fake). Do not import transformers here.

    Modal's ingest worker calls LAION-CLAP and POSTs embeddings back.
    Tests monkeypatch this function to count calls.
    """
    del model_name
    if not wavs:
        return []
    return FakeAudioEmbedder().embed_wavs(wavs)


__all__ = ["AUDIO_DIM", "embed_wavs"]
