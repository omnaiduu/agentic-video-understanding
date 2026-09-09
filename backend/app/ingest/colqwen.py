"""ColQwen seam. Default laptop path is fake; real ColQwen2.x runs on Modal."""

from __future__ import annotations

from app.search.colqwen import FAKE_PATCHES, FakeSlideEmbedder, SLIDE_DIM


def embed_jpegs(jpegs: list[bytes], model_name: str = "") -> list[list[list[float]]]:
    """Default: hash patch vectors (tests / INGEST=fake). Do not import ColQwen here.

    Modal's ingest worker runs ColQwen2.x and POSTs patch lists back.
    Tests monkeypatch this function to count calls.
    """
    del model_name
    if not jpegs:
        return []
    return FakeSlideEmbedder().embed_images(jpegs)


__all__ = ["FAKE_PATCHES", "SLIDE_DIM", "embed_jpegs"]
