"""ColQwen2.x slide embedder. Tests and default laptop runs use FakeSlideEmbedder."""

from __future__ import annotations

import hashlib
import math
from functools import lru_cache
from typing import Protocol

from fastapi import Depends

from app.settings import Settings, get_settings

SLIDE_DIM = 128
FAKE_PATCHES = 8


class SlideEmbedder(Protocol):
    def embed_query(self, text: str) -> list[list[float]]:
        """Token vectors for a search phrase (text side of MaxSim)."""

    def embed_images(self, jpegs: list[bytes]) -> list[list[list[float]]]:
        """Patch vectors per unique slide (vision side of MaxSim)."""


def hash_slide(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    while len(values) < SLIDE_DIM:
        digest = hashlib.sha256(digest).digest()
        values.extend(b - 128.0 for b in digest)
    values = values[:SLIDE_DIM]
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


def maxsim(query: list[list[float]], patches: list[list[float]]) -> float:
    """Sum of per-token max patch dots. Query token `99` can lock onto `$99`."""
    if not query or not patches:
        return 0.0
    score = 0.0
    for token in query:
        best = 0.0
        for patch in patches:
            dot = 0.0
            for left, right in zip(token, patch):
                dot += left * right
            if dot > best:
                best = dot
        score += best
    return score


class FakeSlideEmbedder:
    """No GPU. Optional query_vectors plant token vectors for 'Pro $99'."""

    def __init__(
        self,
        query_vectors: dict[str, list[list[float]]] | None = None,
    ) -> None:
        self.query_vectors = query_vectors or {}

    def embed_query(self, text: str) -> list[list[float]]:
        planted = self.query_vectors.get(text)
        if planted is not None:
            return [list(token) for token in planted]
        tokens = text.split() or [text]
        return [hash_slide("tok:" + token) for token in tokens]

    def embed_images(self, jpegs: list[bytes]) -> list[list[list[float]]]:
        pages: list[list[list[float]]] = []
        for blob in jpegs:
            digest = hashlib.sha256(blob).hexdigest()
            pages.append(
                [hash_slide(f"jpeg:{digest}:{index}") for index in range(FAKE_PATCHES)]
            )
        return pages


class ModalSlideEmbedder:
    """Query tokens via Modal embed_slide_query. Images stay on ingest."""

    def __init__(self, app_name: str, model_name: str) -> None:
        self._app = app_name
        self._model = model_name

    def embed_query(self, text: str) -> list[list[float]]:
        import modal

        phrase = (text or "").strip()
        if not phrase:
            return []
        fn = modal.Function.from_name(self._app, "embed_slide_query")
        tokens = fn.remote(phrase, self._model)
        if not tokens:
            return []
        rows: list[list[float]] = []
        for token in tokens:
            values = [float(x) for x in token]
            if len(values) != SLIDE_DIM:
                raise ValueError(f"slide token must have {SLIDE_DIM} dimensions")
            rows.append(values)
        return rows

    def embed_images(self, jpegs: list[bytes]) -> list[list[list[float]]]:
        raise RuntimeError("slide images are embedded on Modal ingest, not the laptop")


class ColQwenEmbedder:
    """vidore ColQwen2 / 2.5 via colpali-engine. Optional extra; not used in CI."""

    def __init__(self, model_name: str) -> None:
        import torch

        self._torch = torch
        name = (model_name or "").lower()
        if "2.5" in name or "2_5" in name:
            from colpali_engine.models import ColQwen2_5, ColQwen2_5_Processor

            self._model = ColQwen2_5.from_pretrained(model_name).eval()
            self._processor = ColQwen2_5_Processor.from_pretrained(model_name)
        else:
            from colpali_engine.models import ColQwen2, ColQwen2Processor

            self._model = ColQwen2.from_pretrained(model_name).eval()
            self._processor = ColQwen2Processor.from_pretrained(model_name)

    def embed_query(self, text: str) -> list[list[float]]:
        batch = self._processor.process_queries([text])
        with self._torch.no_grad():
            matrix = self._model(**batch)
        row = matrix[0]
        return [[float(x) for x in token.tolist()] for token in row]

    def embed_images(self, jpegs: list[bytes]) -> list[list[list[float]]]:
        if not jpegs:
            return []
        import io

        from PIL import Image

        images = [Image.open(io.BytesIO(blob)).convert("RGB") for blob in jpegs]
        batch = self._processor.process_images(images)
        with self._torch.no_grad():
            matrix = self._model(**batch)
        pages: list[list[list[float]]] = []
        for row in matrix:
            pages.append([[float(x) for x in token.tolist()] for token in row])
        return pages


@lru_cache
def _colqwen(model_name: str) -> ColQwenEmbedder:
    return ColQwenEmbedder(model_name)


def build_slide_embedder(settings: Settings | None = None) -> SlideEmbedder:
    cfg = settings or get_settings()
    if cfg.slide_embedder == "fake":
        return FakeSlideEmbedder()
    if cfg.slide_embedder in ("colqwen", "modal"):
        if cfg.ingest == "modal" or cfg.slide_embedder == "modal":
            return ModalSlideEmbedder(cfg.modal_ingest_app, cfg.colqwen_model)
        return _colqwen(cfg.colqwen_model)
    raise RuntimeError(f"unknown SLIDE_EMBEDDER={cfg.slide_embedder}")


def get_slide_embedder(settings: Settings = Depends(get_settings)) -> SlideEmbedder:
    return build_slide_embedder(settings)
