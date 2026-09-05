# Phase 5 — Picture phone book

**Status:** not locked. Human answers the questions at the bottom first.

Depends on: [Phase 1](phase-01.md) (file + **Postgres**), [Phase 2](phase-02.md) (ffmpeg cuts), [Phase 3](phase-03.md) (JSON loop), [Phase 4](phase-04.md) (**pgvector** already there).

Product (short): after a file is stored, we **index the pictures once**. Later, “where is the red light?” can **find a time** without Gemma looking at two hours.

Related: [SigLIP](../07-models-and-indexes.md) · [tools](../06-tools.md) · [rejected](../04-what-we-rejected.md) · [phase map](../12-build-phases.md)

---

## Where we are

| Done on paper | This phase | Later |
|---|---|---|
| Hold file, scissors, Gemma JSON loop, **speech** notebook | **Pictures** notebook | Sounds (6), export (7), memory (8), website (9+) |

Whisper has **no eyes**. Phase 4 finds spoken words. This phase finds **what it looks like**.

---

## What we are trying to do

Once per file we take about **one photo per second**. A small encoder (**SigLIP 2**) turns each photo into a list of numbers. We save **numbers + time**. We throw away the bulk JPEGs.

When you ask a silent-picture question, our state machine **searches those numbers**. We hand Gemma a few times as **text**. She may then `look` at that time (Phase 2 frames) and `answer`.

Question 2 does **not** re-encode the video.

This **is** RAG (retrieve, then generate). SigLIP finds times; Gemma understands by looking. Search scores are **not** the answer.

---

## What this is not

- **Not** training an embedding model. We download SigLIP 2 and run it.
- **Not** hybrid keyword + dense. Pictures have no words unless we caption every second — we already rejected that ([04](../04-what-we-rejected.md)).
- **Not** Gemma looking. `look` is still Phase 2/3. This only **finds a time**.
- **Not** sound. Chirps and claps are Phase 6 (CLAP).
- **Not** one vector for the whole video. We need *which second*, not *which file*.
- **Not** dumping 2 hours of photos into Gemma.

---

## Why not hybrid like Phase 4

Speech has **words** → keyword (`pricing`) plus meaning (`how much does it cost?`).

Pictures have **pixels**. Keyword search needs text. The only way to get text is to caption every frame with a VLM. That is slow, expensive, and we said no.

SigLIP already puts **photos and phrases in the same number space**. One retrieve: meaning-in-pictures. Phrase `"red light"` → numbers → nearest photo times.

---

## Words

**SigLIP 2** — two sides: photos → vectors, phrases → vectors. Same space. **Search**, don’t narrate. Not a chatbot. Not Gemma.

**1 FPS** — one photo per second **for the phone book**. This is not the look budget (that is still 64 photos per `look`).

**`search_visual`** — a new move in our JSON form, next to `look` / `listen` / `search` / `answer`. **Not** a vLLM tool call. Our Python runs the search.

**pgvector** — same Postgres extension as Phase 4. New table, different numbers (SigLIP size, not E5).

---

## How it will work

**After upload (Phase 1 still saves the file first)**

```
file saved, ffprobe done
       → background ffmpeg ~1 photo / second
       → SigLIP each JPEG → VisualFrame (t, embedding)
       → delete the bulk JPEGs
       → visual_status = ready
```

HTTP upload does **not** wait. Chat can already do “what’s at 0:10?” before the picture book exists. Picture-search only works when `visual_status` is ready.

No video stream (audio-only file) → skip, `visual_status = skipped`. `search_visual` returns empty.

If SigLIP fails: file stays, timed `look` still works.

**Chat (Phase 3 loop, one extra action)**

JSON `do` is now:

- `look` — frames (locked)
- `listen` — wav (locked)
- `search` — speech notebook (locked)
- `search_visual` — `{ "query": "red light" }` → nearest times → next prompt as **text** (`t` + score). No photos in this step.
- `answer`

Example: “where is the red light?” → `search_visual` → hit at 1:04 → maybe `look` 1:03–1:06 → `answer`.

**Caps:** top ~8 hits. Not every second. Gemma still has the Phase 2 look cap if she zooms.

---

## Options (what I would pick)

| Topic | My pick | Other options | Why my pick |
|---|---|---|---|
| Encoder | **SigLIP 2** | 2021 CLIP; Meta PE Core later | Product already locked this. Stronger, multilingual, Apache-2.0. CLIP is the tutorial model we rejected. PE Core is a later swap if sports/CCTV retrieval is weak — **same table, same JSON action**. |
| Checkpoint | **`google/siglip2-so400m-patch16-384`** | `base` (cheaper, a bit worse); `so400m` @ 512 (slower); giant `g` | Sweet spot. Name in config so we can swap. |
| Vectors | **Postgres + pgvector** | FAISS file; sqlite-vec | We already have pgvector from Phase 4. One DB. FAISS is for huge scale we do not have. |
| Sample rate | **1 photo / second** | 0.5 (miss more); 2 (2× cost) | Locked in older docs. Fast blinks can still be missed; Gemma can zoom once a nearby time is found. |
| Keep JPEGs | **Delete after embed** | Keep all for debug | ffmpeg can recreate any frame. 2h × 1 FPS is thousands of files for nothing. |
| What Gemma gets | **Times + scores as text**, then she `look`s | Attach thumbnails in the search step | Thumbnails would eat the look budget and skip verification. Same pattern as Phase 4 speech hits. |
| JSON name | **`search_visual`** | overload `search` with a channel field | Two phone books, two verbs. Prompt stays obvious. |
| Image-to-image | **Not this phase** | User uploads a photo of a bird | Phrase-to-picture is the product. Photo-to-photo can wait. |

**Libraries:** Hugging Face `transformers` + SigLIP 2 weights, ffmpeg CLI (already Phase 2), pgvector (already Phase 4). No CLIP, no CLAP, no captioning VLM, no FAISS.

---

## Plan (agent)

1. `VisualFrame`: video_id, t_s, embedding (pgvector). Index on video_id + vector.
2. `video.visual_status`: pending | processing | ready | error | skipped
3. Background ingest after Phase 1 save: ffmpeg 1 FPS → SigLIP → rows → delete temp JPEGs
4. `search_visual(query)`: embed phrase with SigLIP **text** tower → KNN in this video → top ~8 `{t, score}`
5. Add `search_visual` to the vLLM JSON schema + prompt
6. State machine: run search, append **text** hits, loop (Gemma may then `look`)
7. Tests: inject fake vectors **or** a tiny fixture; `"red square"` finds the painted-red second. Mock SigLIP in unit tests (no GPU, no big weights). Audio-only → skipped. Timed `look` works if visual index is not ready.

Implement **only** this file after 1–4. No CLAP. No export. No website.

---

## Questions (lock these)

1. **Encoder — SigLIP 2, default `so400m-patch16-384`, name in config.** OK? (Not CLIP. Not PE Core in this phase.)
2. **Same Postgres / pgvector** as Phase 4, new table. OK? (Not FAISS.)
3. **Delete sampled JPEGs after vectors are saved.** OK?
4. **1 photo per second** for the phone book. OK?
5. **`search_visual` in the same JSON form** as look / listen / search / answer. Hits as **text times**, then Gemma `look`s. OK?

When these are answered, mark **LOCKED**.

## Done when

- Silent “red light” / “bird” can surface a timestamp from stored picture vectors
- Second question does not re-run SigLIP
- Timed look still works if the picture book is not ready
- Audio-only files skip this index
- Gemma is not fed two hours of photos
- Hits are times, not “the answer”
