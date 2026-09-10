"""SigLIP 2 picture embedder. Tests and default laptop runs use FakeVisualEmbedder."""

from __future__ import annotations

import hashlib
import math
from functools import lru_cache
from typing import Protocol

from fastapi import Depends

from app.settings import Settings, get_settings

VISUAL_DIM = 1152


def _feature_tensor(value):
    """Transformers 5 get_*_features often returns BaseModelOutputWithPooling."""
    pooled = getattr(value, "pooler_output", None)
    if pooled is not None:
        return pooled
    return value


class VisualEmbedder(Protocol):
    def embed_query(self, text: str) -> list[float]:
        """Dense vector for a search phrase (text tower)."""

    def embed_images(self, jpegs: list[bytes]) -> list[list[float]]:
        """Dense vectors for index JPEGs (vision tower)."""


def hash_visual(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    while len(values) < VISUAL_DIM:
        digest = hashlib.sha256(digest).digest()
        values.extend(b - 128.0 for b in digest)
    values = values[:VISUAL_DIM]
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


class FakeVisualEmbedder:
    """No GPU. Optional query_vectors let tests plant a neighbor (red light / bird)."""

    def __init__(self, query_vectors: dict[str, list[float]] | None = None) -> None:
        self.query_vectors = query_vectors or {}

    def embed_query(self, text: str) -> list[float]:
        planted = self.query_vectors.get(text)
        if planted is not None:
            return list(planted)
        return hash_visual("query:" + text)

    def embed_images(self, jpegs: list[bytes]) -> list[list[float]]:
        return [hash_visual("jpeg:" + hashlib.sha256(blob).hexdigest()) for blob in jpegs]


class SiglipEmbedder:
    """google/siglip2-so400m-patch16-384 (or another name in config). Optional extra."""

    def __init__(self, model_name: str) -> None:
        import torch
        from transformers import AutoModel, AutoProcessor

        self._torch = torch
        self._model = AutoModel.from_pretrained(model_name).eval()
        self._processor = AutoProcessor.from_pretrained(model_name)

    def embed_query(self, text: str) -> list[float]:
        import torch

        inputs = self._processor(text=[text], return_tensors="pt")
        with torch.no_grad():
            vector = _feature_tensor(self._model.get_text_features(**inputs))
            vector = vector / vector.norm(p=2, dim=-1, keepdim=True)
        return [float(x) for x in vector[0].tolist()]

    def embed_images(self, jpegs: list[bytes]) -> list[list[float]]:
        if not jpegs:
            return []
        import io

        import torch
        from PIL import Image

        images = [Image.open(io.BytesIO(blob)).convert("RGB") for blob in jpegs]
        inputs = self._processor(images=images, return_tensors="pt")
        with torch.no_grad():
            matrix = _feature_tensor(self._model.get_image_features(**inputs))
            matrix = matrix / matrix.norm(p=2, dim=-1, keepdim=True)
        return [[float(x) for x in row.tolist()] for row in matrix]


@lru_cache
def _siglip(model_name: str) -> SiglipEmbedder:
    return SiglipEmbedder(model_name)


def build_visual_embedder(settings: Settings | None = None) -> VisualEmbedder:
    cfg = settings or get_settings()
    if cfg.visual_embedder == "siglip":
        return _siglip(cfg.siglip_model)
    if cfg.visual_embedder == "fake":
        return FakeVisualEmbedder()
    raise RuntimeError(f"unknown VISUAL_EMBEDDER={cfg.visual_embedder}")


def get_visual_embedder(settings: Settings = Depends(get_settings)) -> VisualEmbedder:
    return build_visual_embedder(settings)
