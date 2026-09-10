from types import SimpleNamespace

from app.search.clap import _feature_tensor as clap_feature
from app.search.siglip import _feature_tensor as siglip_feature


def test_feature_tensor_unwraps_pooler_output() -> None:
    pooled = SimpleNamespace(tolist=lambda: [1.0])
    wrapped = SimpleNamespace(pooler_output=pooled)
    assert siglip_feature(wrapped) is pooled
    assert clap_feature(wrapped) is pooled
    raw = object()
    assert siglip_feature(raw) is raw
