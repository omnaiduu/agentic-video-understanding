# Phase 6 — Sound phone book

**Status: LOCKED** (LAION-CLAP dense search; Python merge+count; **PostgreSQL** + pgvector).

Depends on: [Phase 1](phase-01.md) (file + Postgres), [Phase 2](phase-02.md) (ffmpeg audio), [Phase 3](phase-03.md) (JSON loop), [Phase 4](phase-04.md) / [Phase 5](phase-05.md) (pgvector already there).

Product (short): after a file is stored, we **index the sounds once**. Later, “when did the bird chirp?” can **find a time** without Gemma listening to two hours.

Related: [CLAP](../07-models-and-indexes.md) · [counting](../05-architecture.md) · [rejected](../04-what-we-rejected.md) · [phase map](../12-build-phases.md)

---

## What we are trying to do

Once per file: **3s audio chunks** (1.5s hop) → **LAION-CLAP** → numbers + time. Chat runs **dense search** on that notebook. Gemma gets a few times as **text**, may `listen`, then `answer`. Second question does not run CLAP again.

**Counting** is Python: merge nearby hits, `len()`. Stadium applause may be one blob — “applause 1:00–1:40”, not a fake 847.

This **is** RAG for sounds. Not Whisper (words). Not SigLIP (pictures). Not hybrid (raw audio has no words). Not a clap-only detector.

---

## Locked

**Why still needed:** Whisper will not write “chirp.” SigLIP will not hear a beep.

**Why CLAP not GLAP as default:** sound events are CLAP’s job; speech words are already Whisper. GLAP is a later swap (same table, same JSON action).

**Why Postgres:** same DB as Phases 4–5. New table, different vector size.

---

## Words

**CLAP** — sounds → vectors, phrases → vectors. Search, don’t narrate.  
**Chunk** — a few seconds we embed. Not the 30s `listen` cap.  
**Merge** — hits next to each other are one event.  
**`search_audio`** — JSON action. Our Python (search + count). Not vLLM tools.

---

## How it will work

```
upload → disk + video row (no wait)
       → background ffmpeg 3s chunks, 1.5s hop
       → CLAP each chunk → AudioChunk (start_s, end_s, embedding)
       → audio_status = ready
```

JSON: `look` | `listen` | `search` | `search_visual` | `search_audio` | `answer`

No audio → `audio_status = skipped`. Fail → file stays; timed listen still works.

`search_audio` returns top hits **and** merged clusters + count as **text**. Gemma may then `listen`.

---

## Locked details

| Topic | Decision |
|---|---|
| Encoder | **LAION-CLAP** (default `laion/larger_clap_general` or `clap-htsat-fused`; name in config) |
| Later swap | **GLAP** — same table, same `search_audio` |
| Chunk | **3s**, hop **1.5s** |
| DB | Same PostgreSQL + pgvector, table `AudioChunk` |
| Hits | Top ~8 + merged clusters/count as **text**; Gemma then `listen`s |
| Counting | **Python** merge + `len()` inside `search_audio`. No clap-only detector |
| Chat action | `search_audio` in the vLLM JSON schema |
| Fail | File stays; timed listen still works |

---

## Plan (agent)

1. `AudioChunk`: video_id, start_s, end_s, embedding
2. `video.audio_status`: pending | processing | ready | error | skipped
3. Background ingest: ffmpeg chunks → CLAP → rows
4. `search_audio(query)`: text tower → KNN → merge nearby → hits + count
5. Wire `search_audio` into the Phase 3 loop
6. Tests: inject fake vectors; nearby hits merge to count 1; mute → skipped; mock CLAP (no GPU)

**Libraries:** `transformers` + LAION-CLAP, ffmpeg, pgvector. No Whisper re-run. No SigLIP.

Implement only this file after 1–5.

## Done when

- “When did the bird chirp?” can surface a timestamp
- Second question does not re-run CLAP
- “How many claps?” uses Python merge+count
- Stadium blob is honest (one span)
- Mute files skip this index
- Two hours of audio are not dumped into Gemma
