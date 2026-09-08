"""SigLIP seam. Default laptop path is fake; real SigLIP 2 runs on Modal."""

from __future__ import annotations

from app.search.siglip import FakeVisualEmbedder, VISUAL_DIM


def embed_jpegs(jpegs: list[bytes], model_name: str = "") -> list[list[float]]:
    """Default: hash vectors (tests / INGEST=fake). Do not import transformers here.

    Modal's ingest worker calls SigLIP 2 and POSTs embeddings back.
    Tests monkeypatch this function to count calls.
    """
    del model_name
    if not jpegs:
        return []
    return FakeVisualEmbedder().embed_images(jpegs)


__all__ = ["VISUAL_DIM", "embed_jpegs"]
