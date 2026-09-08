"""Dense picture retrieve: SigLIP text tower vs VisualFrame KNN. Not hybrid."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import bindparam, text
from sqlmodel import Session

from app.search.siglip import VISUAL_DIM, VisualEmbedder

TOP_HITS = 8

_SEARCH_SQL = """
SELECT
    t_s,
    (1.0 - (embedding <=> CAST(:qvec AS vector(1152)))) AS score
FROM visual_frames
WHERE video_id = :vid
  AND embedding IS NOT NULL
ORDER BY embedding <=> CAST(:qvec AS vector(1152)), t_s
LIMIT :top_k
"""


@dataclass(frozen=True)
class VisualHit:
    t: float
    score: float


def _vector_literal(values: list[float]) -> str:
    if len(values) != VISUAL_DIM:
        raise ValueError(f"visual embedding must have {VISUAL_DIM} dimensions")
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


def search_visual(
    session: Session,
    video_id: uuid.UUID,
    query: str,
    embedder: VisualEmbedder,
) -> list[VisualHit]:
    phrase = (query or "").strip()
    if not phrase:
        return []
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
        VisualHit(t=float(row.t_s), score=float(row.score))
        for row in rows
        if row.t_s is not None
    ]
    return hits[:TOP_HITS]
