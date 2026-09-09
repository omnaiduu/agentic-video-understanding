"""Dense slide retrieve: ColQwen query tokens vs SlidePage patches (MaxSim)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlmodel import Session, select

from app.models import SlidePage
from app.search.colqwen import SlideEmbedder, maxsim

TOP_HITS = 8


@dataclass(frozen=True)
class SlideHit:
    t: float
    t_end: float
    score: float
    slide_id: uuid.UUID


def search_slides(
    session: Session,
    video_id: uuid.UUID,
    query: str,
    embedder: SlideEmbedder,
) -> list[SlideHit]:
    phrase = (query or "").strip()
    if not phrase:
        return []
    tokens = embedder.embed_query(phrase)
    rows = session.exec(
        select(SlidePage)
        .where(SlidePage.video_id == video_id)
        .order_by(SlidePage.t_start_s)
    ).all()
    scored: list[SlideHit] = []
    for row in rows:
        patches = row.embeddings or []
        if not patches:
            continue
        scored.append(
            SlideHit(
                t=float(row.t_start_s),
                t_end=float(row.t_end_s),
                score=float(maxsim(tokens, patches)),
                slide_id=row.id,
            )
        )
    scored.sort(key=lambda hit: (-hit.score, hit.t))
    return scored[:TOP_HITS]
