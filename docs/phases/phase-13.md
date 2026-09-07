# Phase 13 — Slide phone book

**Status: LOCKED** (unique-slide dedup + **ColQwen2.x** + `search_slides`).

Depends on: [Phase 1](phase-01.md) (file + Postgres), [Phase 2](phase-02.md) (ffmpeg), [Phase 3](phase-03.md) (JSON loop), [Phase 5](phase-05.md) (1 FPS frames / SigLIP still the object book).

Product (short): after pictures are indexed, we also **index unique slides once**. Later, “which slide had **Pro $99**?” can **find a time** when nobody **said** the number. **Gemma still reads the real frame. ColQwen only finds the time.**

Related: [models](../07-models-and-indexes.md) · [tools](../06-tools.md) · [rejected](../04-what-we-rejected.md) · [phase map](../12-build-phases.md)

---

## What we are trying to do

Talks are a first-class use case. Two different questions:

- “What did she **say** about pricing?” → Whisper `search` (Phase 4). Fine.
- “Which slide had **Pro $99**?” and she never said “ninety-nine.”

| Tool (already in the app) | What it does | Why it misses `$99` |
|---|---|---|
| `search` | Spoken words | Number never spoken |
| `search_visual` (SigLIP) | One vector for the **whole** photo | Tiny text is drowned; every slide “looks like a slide” |
| `look` + Gemma | **Reads** the slide | Only if we already know the time |

The gap is the **finder**, not the reader. Do not OCR every frame. Do not caption every second. Add a **slide map**, then the same loop: find time → `look` → Gemma answers.

This **is** RAG. ColQwen finds times; Gemma understands by looking. Search scores are **not** the answer. Not a replacement for SigLIP (bird / red light). Not Whisper.

---

## Two problems (do not mix them)

### 1 — too many copies of the same slide

At **1 FPS**, a 40-minute deck with **40 slides** is ~**2,400 photos**. Slide 7 stays up for a minute → 60 twins. Search gets muddy.

**Fix: dedup.** If this frame is almost the same as the last **kept** frame, don’t store another copy. Keep **one image + a time span** (`12:04–12:58`).

That is **not** PySceneDetect. Scene detect finds **movie cuts**. A lecture can change slides with **no cut**, or cut the camera while the slide stays. Compare **pixels of the screen**, not edits.

**How:** perceptual hash (pHash) on the frame or the slide region; or SigLIP cosine vs last kept frame (very high similarity = same slide). Optional: hash the deck area, ignore a talking-head strip.

**When it helps:** static pictures — slides, shared PDF, talking-head with the same wall. **Sports / motion:** almost every frame is different; little savings. **CCTV empty hallway:** saves copies, but the threshold must not drop the one second a person appears.

Dedup does **not** read `$99`. ColQwen runs on **unique slides**, not on 2,400 frames.

### 2 — SigLIP cannot read the slide

SigLIP is the right tool for **objects and scenes**. It is the wrong tool for **a specific string on a busy slide**.

**Fix: ColQwen2.x** (ColPali family) on those **unique** slides. Search like visual **PDF RAG**: match query words to **patches** of the page. Then Gemma still opens that timestamp and reads.

---

## Locked

**Why ColQwen2.x:** ColPali (ICLR 2025, PaliGemma) invented patch-level late interaction. ColQwen2 / ColQwen2.5 is the same recipe on Qwen2-VL / Qwen2.5-VL — stronger on small fonts, dense slides, more languages. ColPali is the ancestor, not the default.

**Why not every 1 FPS frame:** hundreds of vectors per page × 2,400 frames is huge. After dedup, ~40 slides × MaxSim is cheap.

**Why not replace `search_visual`:** different questions. SigLIP stays for bird / red light. `search_slides` is for printed text / layout.

**Why Gemma still looks:** embeddings lie. Google still opens frames.

---

## Words

**ColQwen2.x** — slide → many patch vectors; query → token vectors; **MaxSim** scores the page. Retriever, not chatbot.  
**Unique slide** — one kept frame + time range after dedup.  
**`search_slides`** — JSON action. Our Python. Returns times, not answers.

---

## How it will work

```
upload → disk + video row (no wait)
       → (Phase 5) ffmpeg ~1 photo / second → SigLIP → VisualFrame
       → unique slides + time ranges (pHash and/or SigLIP vs last kept)
       → ColQwen2.x on unique slides only → SlidePage (pgvector multi-vector)
       → slides_status = ready
```

JSON: `look` | `listen` | `search` | `search_visual` | `search_audio` | `search_slides` | `export_*` | `answer`

Audio-only / no frames → `slides_status = skipped`. Fail → file stays; timed look still works.

```
search_slides “Pro $99” → 12:04
look 12:04–12:08 → Gemma reads the real frame
answer + timestamp
```

---

## Locked details

| Topic | Decision |
|---|---|
| Encoder | **ColQwen2.x** (config name, e.g. vidore ColQwen2 / 2.5). Fallback **ColPali** if this model is painful |
| Not | OCR every frame; VLM captions; replace SigLIP; Qdrant/Vespa for one lecture |
| Dedup | **pHash and/or SigLIP vs previous kept frame**. Not scene detect |
| DB | Same PostgreSQL + pgvector. Table `SlidePage`: video_id, t_start, t_end, patch embeddings |
| Hits | Top ~8 `{t, score, slide_id}` as **text**; Gemma then `look`s |
| Chat action | `search_slides` in the vLLM JSON schema |
| Reader | Gemma on `look` — unchanged |
| Last-ditch read | optional later `ocr_frame` on **one** fetched frame — **not this phase** |
| Fail | File stays; timed look still works |

**How ColQwen scores (do not skip):**

1. A slide is a **grid of patches**, not one vector.
2. Each patch → a short ColBERT-style vector (~128-d). SigLIP: **one** vector for the whole photo.
3. Query is text only: one vector per token (`Pro`, `$`, `99`).
4. **MaxSim:** for each query token, best matching patch, then **sum**. Token `99` can lock onto `$99` even if most of the slide is a speaker photo.
5. Trained as **retrieval** (this question ↔ this page), not OCR.

---

## Plan (agent)

1. `SlidePage`: video_id, t_start_s, t_end_s, embeddings. Index on video_id
2. `video.slides_status`: pending | processing | ready | error | skipped
3. Background ingest: unique-frame dedup on the 1 FPS stream → ColQwen on uniques → rows
4. `search_slides(query)`: ColQwen query → MaxSim in this video → top ~8
5. Wire `search_slides` into the Phase 3 loop (same JSON schema as the other `search_*`)
6. Tests: fake patch vectors / tiny fixture; mock ColQwen in unit tests (no GPU)

**Libraries:** ColQwen2.x (vidore / transformers as on the implementation-pass card), ffmpeg, pgvector. No OCR-all-frames, no extra vector DB, no new UI kit.

Implement only this file after 1–12.

## Done when

- “Which slide had **Pro $99**?” (text nobody spoke) surfaces a timestamp
- Gemma **looks** at that time and answers from the **real frame**
- Second question does not re-run ColQwen
- Timed look works if the slide book is not ready
- Audio-only files skip this index
- SigLIP `search_visual` still exists and still finds birds / red lights
- Unique slides, not 2,400 copies of slide 7, go into ColQwen
