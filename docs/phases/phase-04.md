# Phase 4 — Speech phone book

**Status: LOCKED** (hybrid RAG on Whisper text; **PostgreSQL**, not SQLite).

Depends on: [Phase 1](phase-01.md) (file — **DB corrected to Postgres**), [Phase 3](phase-03.md) (JSON loop).

Product (short): after a file is stored, we **write down the words once**. Later, “what did she say about pricing?” can **find a time** without Gemma listening to two hours.

Related: [Whisper](../07-models-and-indexes.md) · [tools](../06-tools.md) · [phase map](../12-build-phases.md)

---

## What we are trying to do

Whisper listens to the whole file **once**. We save lines with times. Chat runs **hybrid search** on that notebook. Gemma gets a few hits, may `look`, then `answer`. Second question does not run Whisper again.

This **is** RAG (retrieve, then generate). Whisper writes words; the retriever finds lines; Gemma understands. Not raw-audio CLAP (that is sounds, later).

---

## Locked: hybrid + Postgres

**Why Postgres:** you prefer it. One DB for videos, chat, keyword search, and vectors. SQLModel stays; `DATABASE_URL` is Postgres. Files still on disk.

**Hybrid = two retrieves, then merge**

1. **Keyword** — Postgres `tsvector` + GIN + `plainto_tsquery` / `ts_rank`. Exact words: “pricing”, names.
2. **Meaning** — small **text** embedder we do not train (default **E5-small**, name in config) → `vector` column + **pgvector**. Paraphrase: “how much does it cost?”
3. **Merge** — Reciprocal Rank Fusion. Top ~8 `{t, text}` into the next prompt as **text**.

---

## Words

**tsvector** — Postgres full-text (keyword).  
**pgvector** — vectors in Postgres.  
**RRF** — mix two ranked lists.  
**`search`** — JSON action beside look / listen / answer. Our Python. Not vLLM tools.

---

## How it will work

```
upload → disk + video row in Postgres (no wait for Whisper)
       → background faster-whisper
       → segments: text, times, tsv, embedding
       → transcript_status = ready
```

JSON: `look` | `listen` | `search` | `answer`

---

## Locked details

| Topic | Decision |
|---|---|
| DB | PostgreSQL + SQLModel + psycopg + pgvector |
| Keyword | tsvector / GIN |
| Dense | E5-small (or MiniLM via config) |
| Merge | RRF, ~8 hits |
| Whisper | faster-whisper **turbo** (model name swappable) |
| Ingest | Background |
| Fail | File stays; timed look still works |

---

## Plan (agent)

1. Postgres + `CREATE EXTENSION vector`
2. `TranscriptLine`: video_id, start_s, end_s, text, tsv, embedding
3. Ingest: Whisper → rows
4. `search_transcript`: FTS + KNN + RRF
5. Wire `search` into the Phase 3 loop
6. Tests on Postgres; mock Whisper in unit tests

**Libraries:** faster-whisper, sentence-transformers (E5), pgvector, psycopg. No SigLIP/CLAP.

Implement only this file after 1–3.

## Done when

- “pricing” and a paraphrase both can surface a time
- Second question does not run Whisper
- Timed look works if transcript is not ready
- Whole talk is not dumped into Gemma
