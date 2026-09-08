"""Hybrid transcript retrieve: FTS + pgvector KNN, merged with RRF."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import bindparam, text
from sqlmodel import Session

from app.search.embed import EMBED_DIM, Embedder

CANDIDATE_DEPTH = 40
RRF_K = 60
TOP_HITS = 8

_SEARCH_SQL = """
WITH fts_all AS (
    SELECT
        id,
        start_s,
        text,
        row_number() OVER (
            ORDER BY ts_rank(tsv, plainto_tsquery('english', :query)) DESC, start_s
        ) AS rank
    FROM transcript_lines
    WHERE video_id = :vid
      AND tsv @@ plainto_tsquery('english', :query)
),
fts AS (
    SELECT * FROM fts_all WHERE rank <= :depth
),
knn_all AS (
    SELECT
        id,
        start_s,
        text,
        row_number() OVER (
            ORDER BY embedding <=> CAST(:qvec AS vector(384)), start_s
        ) AS rank
    FROM transcript_lines
    WHERE video_id = :vid
      AND embedding IS NOT NULL
),
knn AS (
    SELECT * FROM knn_all WHERE rank <= :depth
)
SELECT
    COALESCE(fts.start_s, knn.start_s) AS start_s,
    COALESCE(fts.text, knn.text) AS text
FROM fts
FULL OUTER JOIN knn ON fts.id = knn.id
ORDER BY
    COALESCE(1.0 / (:rrf_k + fts.rank), 0)
    + COALESCE(1.0 / (:rrf_k + knn.rank), 0) DESC,
    COALESCE(fts.start_s, knn.start_s)
LIMIT :top_k
"""


@dataclass(frozen=True)
class TranscriptHit:
    t: float
    text: str


def _vector_literal(values: list[float]) -> str:
    if len(values) != EMBED_DIM:
        raise ValueError(f"embedding must have {EMBED_DIM} dimensions")
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


def search_transcript(
    session: Session,
    video_id: uuid.UUID,
    query: str,
    embedder: Embedder,
) -> list[TranscriptHit]:
    phrase = (query or "").strip()
    if not phrase:
        return []
    qvec = _vector_literal(embedder.embed_query(phrase))
    rows = session.execute(
        text(_SEARCH_SQL).bindparams(
            bindparam("query"),
            bindparam("vid"),
            bindparam("qvec"),
            bindparam("depth"),
            bindparam("rrf_k"),
            bindparam("top_k"),
        ),
        {
            "query": phrase,
            "vid": video_id,
            "qvec": qvec,
            "depth": CANDIDATE_DEPTH,
            "rrf_k": RRF_K,
            "top_k": TOP_HITS,
        },
    ).all()
    hits = [
        TranscriptHit(t=float(row.start_s), text=str(row.text))
        for row in rows
        if row.start_s is not None and row.text
    ]
    return hits[:TOP_HITS]
