from __future__ import annotations

import sys
import types

from app.search.clap import AUDIO_DIM, FakeAudioEmbedder, ModalAudioEmbedder, build_audio_embedder
from app.search.embed import EMBED_DIM, FakeEmbedder, ModalE5Embedder, build_embedder
from app.search.siglip import VISUAL_DIM, FakeVisualEmbedder, ModalVisualEmbedder, build_visual_embedder
from app.settings import Settings


def test_fake_embedder_default() -> None:
    emb = build_embedder(Settings(ingest="fake", embedder="fake"))
    assert isinstance(emb, FakeEmbedder)


def test_e5_with_modal_ingest_uses_remote() -> None:
    emb = build_embedder(
        Settings(
            ingest="modal",
            embedder="e5",
            modal_ingest_app="agentic-video-ingest",
        )
    )
    assert isinstance(emb, ModalE5Embedder)


def test_modal_e5_embedder_calls_remote(monkeypatch) -> None:
    seen: dict = {}

    class Fn:
        def remote(self, text, model):
            seen["text"] = text
            seen["model"] = model
            return [0.1] * EMBED_DIM

    class Function:
        @staticmethod
        def from_name(app, name):
            seen["app"] = app
            seen["name"] = name
            return Fn()

    fake = types.ModuleType("modal")
    fake.Function = Function
    monkeypatch.setitem(sys.modules, "modal", fake)
    emb = ModalE5Embedder("agentic-video-ingest", "intfloat/e5-small-v2")
    vector = emb.embed_query("pricing")
    assert seen["name"] == "embed_text_query"
    assert seen["text"] == "query: pricing"
    assert len(vector) == EMBED_DIM


def test_siglip_with_modal_ingest_uses_remote() -> None:
    emb = build_visual_embedder(
        Settings(
            ingest="modal",
            visual_embedder="siglip",
            modal_ingest_app="agentic-video-ingest",
        )
    )
    assert isinstance(emb, ModalVisualEmbedder)


def test_clap_with_modal_ingest_uses_remote() -> None:
    emb = build_audio_embedder(
        Settings(
            ingest="modal",
            audio_embedder="clap",
            modal_ingest_app="agentic-video-ingest",
        )
    )
    assert isinstance(emb, ModalAudioEmbedder)


def test_modal_visual_embedder_calls_remote(monkeypatch) -> None:
    seen: dict = {}

    class Fn:
        def remote(self, query, model):
            seen["query"] = query
            seen["model"] = model
            return [0.2] * VISUAL_DIM

    class Function:
        @staticmethod
        def from_name(app, name):
            seen["name"] = name
            return Fn()

    fake = types.ModuleType("modal")
    fake.Function = Function
    monkeypatch.setitem(sys.modules, "modal", fake)
    emb = ModalVisualEmbedder("agentic-video-ingest", "google/siglip2-so400m-patch16-384")
    vector = emb.embed_query("a rabbit")
    assert seen["name"] == "embed_visual_query"
    assert seen["query"] == "a rabbit"
    assert len(vector) == VISUAL_DIM


def test_modal_audio_embedder_calls_remote(monkeypatch) -> None:
    seen: dict = {}

    class Fn:
        def remote(self, query, model):
            seen["query"] = query
            return [0.3] * AUDIO_DIM

    class Function:
        @staticmethod
        def from_name(app, name):
            seen["name"] = name
            return Fn()

    fake = types.ModuleType("modal")
    fake.Function = Function
    monkeypatch.setitem(sys.modules, "modal", fake)
    emb = ModalAudioEmbedder("agentic-video-ingest", "laion/larger_clap_general")
    vector = emb.embed_query("a beep")
    assert seen["name"] == "embed_audio_query"
    assert seen["query"] == "a beep"
    assert len(vector) == AUDIO_DIM


def test_local_fake_visual_and_audio_unchanged() -> None:
    assert isinstance(
        build_visual_embedder(Settings(ingest="fake", visual_embedder="fake")),
        FakeVisualEmbedder,
    )
    assert isinstance(
        build_audio_embedder(Settings(ingest="fake", audio_embedder="fake")),
        FakeAudioEmbedder,
    )
