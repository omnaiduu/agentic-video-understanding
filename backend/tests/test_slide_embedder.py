from __future__ import annotations

import sys
import types

from app.search.colqwen import (
    SLIDE_DIM,
    FakeSlideEmbedder,
    ModalSlideEmbedder,
    build_slide_embedder,
)
from app.settings import Settings


def test_fake_slide_embedder_default() -> None:
    emb = build_slide_embedder(
        Settings(ingest="fake", slide_embedder="fake")
    )
    assert isinstance(emb, FakeSlideEmbedder)


def test_colqwen_with_modal_ingest_uses_remote() -> None:
    emb = build_slide_embedder(
        Settings(
            ingest="modal",
            slide_embedder="colqwen",
            modal_ingest_app="agentic-video-ingest",
        )
    )
    assert isinstance(emb, ModalSlideEmbedder)


def test_modal_slide_embedder_calls_remote(monkeypatch) -> None:
    seen: dict = {}

    class Fn:
        def remote(self, query, model):
            seen["query"] = query
            seen["model"] = model
            return [[0.25] * SLIDE_DIM, [-0.1] * SLIDE_DIM]

    class Function:
        @staticmethod
        def from_name(app, name):
            seen["app"] = app
            seen["name"] = name
            return Fn()

    fake = types.ModuleType("modal")
    fake.Function = Function
    monkeypatch.setitem(sys.modules, "modal", fake)
    emb = ModalSlideEmbedder("agentic-video-ingest", "vidore/colqwen2.5-v0.2")
    tokens = emb.embed_query("Pro $99")
    assert seen["name"] == "embed_slide_query"
    assert seen["query"] == "Pro $99"
    assert len(tokens) == 2
    assert len(tokens[0]) == SLIDE_DIM
