# Slides and on-screen text — find, then Gemma reads

Plain-language plan from the design thread: **two problems, two fixes, one extra tool.** Not a second product. Not v1-blocking. Code is not in this repo yet.

The picture book we already locked is **SigLIP 2** (`search_visual`): “this frame *looks like* a bird / red light.” That stays. This note is only for **text, numbers, charts, and tables printed on screen** — mostly **talks and slides** — when nobody **said** the words into the mic.

Gemma still **reads** the real frame. These tools only help **find the second**.

---

## Why this exists

Talks are a first-class use case (lectures, keynotes, webinars, courses). Users will ask:

- “What did she **say** about pricing?” → transcript ([WhisperX](13-whisperx.md)). Fine.
- “Which slide had **Pro $99**?” and she **never said** “ninety-nine.”

Today’s tools fail that second question:

| Tool | What it does | Why it misses `$99` |
|---|---|---|
| `search_transcript` | Spoken words | Number never spoken |
| `search_visual` (SigLIP / CLIP) | One vector for the **whole** photo | Tiny text is drowned; every slide “looks like a slide” |
| `get_frames` + Gemma | **Reads** the slide | Only if we already know the time |

So: **finder is the gap, not the reader.** We do **not** OCR every frame. We do **not** caption every second with a VLM. We add a **slide map**, then the same loop: find time → `get_frames` → Gemma answers.

---

## Two problems (do not mix them)

### Problem 1 — too many copies of the same slide

At **1 FPS**, a 40-minute deck with **40 slides** is about **2,400 photos**. Slide 7 stays up for a minute → 60 almost-identical frames. Wasteful. Search gets muddy (60 twins for “pricing slide”).

**Fix: dedup.** If this frame is almost the same as the last **kept** frame, don’t store another copy. Keep **one image + a time span** (`12:04–12:58`).

That is **not** PySceneDetect. Scene detect finds **movie cuts**. A lecture can change slides with **no cut**, or cut the camera while the slide stays. We compare **pixels of the screen**, not edits.

**How (cheap → better):** perceptual hash (pHash) on the frame or the slide region; or SigLIP cosine vs last kept frame (e.g. very high similarity = same slide). Optional: hash the deck area, ignore a talking-head strip.

**When it helps:** any **static** picture — slides, shared PDF, talking-head with the same wall. **Sports / motion:** almost every frame is different; little savings. **CCTV empty hallway:** saves copies, but the threshold must not drop the one second a person appears.

Dedup does **not** read `$99`. It only makes the picture book smaller and cleaner. ColQwen should run on **unique slides**, not on 2,400 frames.

### Problem 2 — CLIP cannot read the slide

SigLIP is the right tool for **objects and scenes**. It is the wrong tool for **a specific string on a busy slide**.

**Fix: ColQwen (ColPali family)** on those **unique** slides. Search like visual **PDF RAG**: match query words to **patches** of the page. Then Gemma still opens that timestamp and reads.

This **is** slideshow RAG. In this product it is one extra search tool, not a new app.

---

## When this is useful (and when it is not)

**Use the extra path when:** the question is about **what is printed on screen**, and speech + SigLIP both miss it.

Helps:

- “Which slide had **Pro $99**?”
- “When did they show the diagram with **KV cache**?”
- “Find the table with **Q3 revenue**.”
- “The slide that said **don’t use scene detect** — timestamp?”
- Same idea: Zoom **shared PDF**, tutorial **IDE / terminal / error text** (document-like frames)

Does **not** replace:

| User asks | Use |
|---|---|
| “What did she say about pricing?” | WhisperX / `search_transcript` |
| “Flying bird / red light / yellow jacket” | SigLIP / `search_visual` |
| “When did people clap?” | GLAP / `search_audio` |
| “Summarize the talk” | Transcript (+ a bit of video) |
| Already know the time | `get_frames` — Gemma reads; skip ColQwen |

If first demos are bird / clap / “what did she say?”, **ship without ColQwen.** Maybe still **dedup** so SigLIP isn’t 2,400 copies of slide 7. Add ColQwen when slide/text questions fail.

Scorebugs, license plates, tiny TV overlays: same *idea*, weaker fit (models were trained on **pages**). Not the main win.

---

## The tool

Name: **`search_slides`** (or ColQwen behind visual search **only for unique deck-like frames**). Same job as the other `search_*` tools: **return times**. Not answers.

```
upload
  → ffmpeg ~1 FPS
  → Problem 1: unique slides + time ranges
  → SigLIP on frames (or uniques)     search_visual   bird / red light
  → ColQwen on unique slides only     search_slides   “Pro $99”
  → get_frames(t) → Gemma reads
```

| Tool | Input | Output | Role |
|---|---|---|---|
| `search_slides` | phrase | `[{t, score, slide_id}]` | Find **which unique slide** matches on-screen text/layout |
| `get_frames` | start, end, fps | images to Gemma | **Read** — unchanged |

v1 tools in [06-tools.md](06-tools.md) stay as they are. This is **later / if slides fail**, next to optional `ocr_frame` (OCR **one** already-opened frame if 12B still misreads). ColQwen **finds**; `ocr_frame` is a last-ditch **read**. Prefer not to OCR the whole video.

---

## How ColQwen works (key parts)

**ColPali** (ICLR 2025, PaliGemma) invented the recipe. **ColQwen / ColQwen2 / ColQwen2.5** is the same idea on **Qwen2-VL / Qwen2.5-VL**. We pick **ColQwen2.x** as the default: stronger on small fonts, dense slides, more languages. ColPali is the ancestor, not the 2026 default.

They are **retrievers**, not chatbots.

1. **A slide is a grid of patches**, not one vector. Each patch might be a word, a bar in a chart, a table cell.
2. Vision encoder + language model → each patch becomes a **short** vector (ColBERT-style, ~128-d). One slide → hundreds of vectors. SigLIP: **one** vector for the whole photo.
3. The **query** is text only: one vector per token (`Pro`, `$`, `99`, …).
4. **Late interaction (MaxSim):** for each query token, take the **best** matching patch, then **sum**. Token `99` can lock onto the `$99` patch even if most of the slide is a speaker photo.
5. **Trained as retrieval** (this question ↔ this page), not as OCR (emit a string). Gemma still does QA on the chosen frame.

**Why not run it on every second of video:** hundreds of vectors per page × 2,400 frames is huge. After problem 1, ~40 slides × MaxSim is cheap. Fancy ANN (Qdrant/Vespa two-stage) is for **libraries of PDFs**, not one lecture.

---

## Models — what we choose and why

| Piece | Choice | Why |
|---|---|---|
| Scene / object search | **SigLIP 2** (keep) | Still the visual index for bird, red light, people. CLIP 2021 is worse. |
| Collapse duplicate frames | **pHash and/or SigLIP vs previous** | Problem 1. Not scene detect. |
| On-screen text / slide search | **ColQwen2.x** | Same ColPali recipe, better eyes for dense text. Apache-friendly Qwen-VL line. |
| Fallback if ColQwen is painful | **ColPali** | Original, PaliGemma; slightly weaker on small fonts. |
| Reader | **Gemma 4** on `get_frames` | Locked brain. Answers from rewatch, not from search scores. |
| Last-ditch read | optional `ocr_frame` | One fetched frame, not ingest. |
| Not chosen | OCR every frame; VLM captions at ingest; E2B-as-embedder | Already rejected. Expensive or the wrong job. |

SigLIP and ColQwen **both** can exist. Different questions. Do not replace `search_visual` with ColQwen.

---

## Why this way (not the tempting alternatives)

| Tempting idea | Why not |
|---|---|
| Let Gemma skim 2h of slides | Slow/$; ~60s video gulp |
| Caption every slide with a VLM at ingest (`search_notes`) | Thousands of LLM calls; we already refused this |
| OCR every frame | Brittle, expensive; ColQwen **skips** OCR for **finding** |
| Answer from ColQwen scores only | Embeddings lie; Google still opens frames |
| Scene detect as the slide finder | Cuts ≠ new slide |
| One SigLIP vector but “try harder” | Architecture cannot attend to a tiny `$99` patch the way MaxSim can |

---

## Build order (don’t skip to ColQwen)

1. **v1 as locked:** transcript + SigLIP + GLAP + Gemma rewatch. Prove talk / bird / clap.
2. **Dedup unique frames** at ingest (problem 1). Helps SigLIP even before ColQwen.
3. If “what’s on the slide?” fails in real use: **ColQwen on uniques** + `search_slides` + same `get_frames`.
4. Only if Gemma still misreads a dense slide: `ocr_frame` on that one frame.

Done for *this* slice when: a lecture answers “which slide had [text nobody spoke]?” with a timestamp, without loading the whole video into Gemma, and without OCR-all-frames.

---

## Related docs

- [What’s new vs this design](12-whats-new-2026.md) — ColQwen in the 2026 shopping list
- [WhisperX](13-whisperx.md) — spoken words; cannot see `$99`
- [Tools](06-tools.md) — v1 tools; this is a later `search_*`
- [What we rejected](04-what-we-rejected.md) — no VLM ingest, no OCR-every-frame, no scene-detect spine
- [Implementation plan](09-implementation-plan.md) — polish step: ColQwen if slides fail
