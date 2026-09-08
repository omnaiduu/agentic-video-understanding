"""Dense sound retrieve: CLAP text tower vs AudioChunk KNN, then Python merge+count."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import bindparam, text
from sqlmodel import Session

from app.search.clap import AUDIO_DIM, AudioEmbedder

TOP_HITS = 8
MERGE_GAP_S = 1.5

_SEARCH_SQL = """
SELECT
    start_s,
    end_s,
    (1.0 - (embedding <=> CAST(:qvec AS vector(512)))) AS score
FROM audio_chunks
WHERE video_id = :vid
  AND embedding IS NOT NULL
ORDER BY embedding <=> CAST(:qvec AS vector(512)), start_s
LIMIT :top_k
"""


@dataclass(frozen=True)
class AudioHit:
    start_s: float
    end_s: float
    score: float

    @property
    def t(self) -> float:
        return self.start_s


@dataclass(frozen=True)
class AudioCluster:
    start_s: float
    end_s: float
    n_hits: int


@dataclass(frozen=True)
class AudioSearchResult:
    hits: list[AudioHit]
    clusters: list[AudioCluster]
    count: int


def _vector_literal(values: list[float]) -> str:
    if len(values) != AUDIO_DIM:
        raise ValueError(f"audio embedding must have {AUDIO_DIM} dimensions")
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


def merge_clusters(hits: list[AudioHit], gap_s: float = MERGE_GAP_S) -> list[AudioCluster]:
    """Nearby/overlapping hits are one event. Stadium applause is one blob."""
    if not hits:
        return []
    ordered = sorted(hits, key=lambda hit: (hit.start_s, hit.end_s))
    groups: list[list[AudioHit]] = [[ordered[0]]]
    for hit in ordered[1:]:
        last = groups[-1]
        last_end = max(item.end_s for item in last)
        if hit.start_s <= last_end + gap_s:
            last.append(hit)
        else:
            groups.append([hit])
    return [
        AudioCluster(
            start_s=min(item.start_s for item in group),
            end_s=max(item.end_s for item in group),
            n_hits=len(group),
        )
        for group in groups
    ]


def search_audio(
    session: Session,
    video_id: uuid.UUID,
    query: str,
    embedder: AudioEmbedder,
) -> AudioSearchResult:
    phrase = (query or "").strip()
    if not phrase:
        return AudioSearchResult(hits=[], clusters=[], count=0)
    qvec = _vector_literal(embedder.embed_query(phrase))
    rows = session.execute(
        text(_SEARCH_SQL).bindparams(
            bindparam("vid"),
            bindparam("qvec"),
            bindparam("top_k"),
        ),
        {"vid": video_id, "qvec": qvec, "top_k": TOP_HITS},
    ).all()
    hits = [
        AudioHit(
            start_s=float(row.start_s),
            end_s=float(row.end_s),
            score=float(row.score),
        )
        for row in rows
        if row.start_s is not None and row.end_s is not None
    ][:TOP_HITS]
    clusters = merge_clusters(hits)
    return AudioSearchResult(hits=hits, clusters=clusters, count=len(clusters))
