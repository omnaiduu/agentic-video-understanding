# Phase 5 — Picture phone book

**Status: LOCKED** (SigLIP 2 dense search; **PostgreSQL** + pgvector).

Depends on: [Phase 1](phase-01.md) (file + Postgres), [Phase 2](phase-02.md) (ffmpeg), [Phase 3](phase-03.md) (JSON loop), [Phase 4](phase-04.md) (pgvector already there).

Product (short): after a file is stored, we **index the pictures once**. Later, “where is the red light?” can **find a time** without Gemma looking at two hours.

Related: [SigLIP](../07-models-and-indexes.md) · [tools](../06-tools.md) · [rejected](../04-what-we-rejected.md) · [phase map](../12-build-phases.md)

---

## What we are trying to do

Once per file: ~**one photo per second** → **SigLIP 2** → numbers + time. Chat runs **dense search** on that notebook. Gemma gets a few times as **text**, may `look`, then `answer`. Second question does not run SigLIP again.

This **is** RAG (retrieve, then generate). SigLIP finds times; Gemma understands by looking. Search scores are **not** the answer. Not hybrid (pictures have no words). Not sound (that is Phase 6).

---

## Locked

**Why dense only:** speech has words (Phase 4 hybrid). Pictures have pixels. Keyword would need captions every second — we rejected that. SigLIP already maps photos and phrases into the same number space.

**Why Postgres:** same DB as Phase 4. New table, different vector size (SigLIP, not E5).

---

## Words

**SigLIP 2** — photos → vectors, phrases → vectors. Search, don’t narrate.  
**1 FPS** — phone-book sample rate. Not the look budget (still 64 photos).  
**`search_visual`** — JSON action beside look / listen / search / answer. Our Python. Not vLLM tools.

---

## How it will work

```
upload → disk + video row (no wait)
       → background ffmpeg ~1 photo / second
       → SigLIP each JPEG → VisualFrame (t, embedding)
       → delete bulk JPEGs
       → visual_status = ready
```

JSON: `look` | `listen` | `search` | `search_visual` | `answer`

Audio-only → `visual_status = skipped`. Fail → file stays; timed look still works.

---

## Locked details

| Topic | Decision |
|---|---|
| Encoder | **SigLIP 2**, default **`google/siglip2-so400m-patch16-384`** (name in config) |
| Not | 2021 CLIP; PE Core (later swap, same table + action) |
| DB | Same PostgreSQL + pgvector, table `VisualFrame` |
| Sample | **1 photo per second** |
| JPEGs | **Delete** after embed (ffmpeg can recreate) |
| Hits | Top ~8 `{t, score}` as **text**; Gemma then `look`s |
| Chat action | `search_visual` in the vLLM JSON schema |
| Image-to-image | Not this phase |
| Fail | File stays; timed look still works |

---

## Plan (agent)

1. `VisualFrame`: video_id, t_s, embedding. Index on video_id + vector
2. `video.visual_status`: pending | processing | ready | error | skipped
3. Background ingest: ffmpeg 1 FPS → SigLIP → rows → delete temp JPEGs
4. `search_visual(query)`: SigLIP text tower → KNN in this video → top ~8
5. Wire `search_visual` into the Phase 3 loop
6. Tests: inject fake vectors or a tiny fixture; mock SigLIP in unit tests (no GPU)

**Libraries:** `transformers` + SigLIP 2, ffmpeg, pgvector. No CLIP, no CLAP, no FAISS.

Implement only this file after 1–4.

## Done when

- Silent “red light” / “bird” can surface a timestamp
- Second question does not re-run SigLIP
- Timed look works if the picture book is not ready
- Audio-only files skip this index
- Two hours of photos are not dumped into Gemma
