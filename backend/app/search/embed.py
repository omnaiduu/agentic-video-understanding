"""Text embedders. Tests and default laptop runs use FakeEmbedder (no torch)."""

from __future__ import annotations

import hashlib
import math
from functools import lru_cache
from typing import Protocol

from fastapi import Depends

from app.settings import Settings, get_settings

EMBED_DIM = 384


class Embedder(Protocol):
    def embed_query(self, text: str) -> list[float]:
        """Dense vector for a search phrase."""

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        """Dense vectors for transcript lines."""


def hash_vector(text: str) -> list[float]:
    """Deterministic 384-d unit vector. Not semantic; tests plant real neighbors."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    while len(values) < EMBED_DIM:
        digest = hashlib.sha256(digest).digest()
        values.extend(b - 128.0 for b in digest)
    values = values[:EMBED_DIM]
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


class FakeEmbedder:
    """No GPU. Optional query_vectors let tests plant a paraphrase neighbor."""

    def __init__(self, query_vectors: dict[str, list[float]] | None = None) -> None:
        self.query_vectors = query_vectors or {}

    def embed_query(self, text: str) -> list[float]:
        planted = self.query_vectors.get(text)
        if planted is not None:
            return list(planted)
        return hash_vector("query:" + text)

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return [hash_vector("passage:" + text) for text in texts]


class E5Embedder:
    """intfloat/e5-small-v2 (or another sentence-transformers name). Optional extra."""

    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)

    def embed_query(self, text: str) -> list[float]:
        vector = self._model.encode(
            "query: " + text,
            normalize_embeddings=True,
        )
        return [float(x) for x in vector.tolist()]

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        prefixed = ["passage: " + text for text in texts]
        matrix = self._model.encode(prefixed, normalize_embeddings=True)
        return [[float(x) for x in row.tolist()] for row in matrix]


@lru_cache
def _e5(model_name: str) -> E5Embedder:
    return E5Embedder(model_name)


def build_embedder(settings: Settings | None = None) -> Embedder:
    cfg = settings or get_settings()
    if cfg.embedder == "e5":
        return _e5(cfg.embed_model)
    if cfg.embedder == "fake":
        return FakeEmbedder()
    raise RuntimeError(f"unknown EMBEDDER={cfg.embedder}")


def get_embedder(settings: Settings = Depends(get_settings)) -> Embedder:
    return build_embedder(settings)
