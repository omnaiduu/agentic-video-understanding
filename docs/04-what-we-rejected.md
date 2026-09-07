# What we rejected (and why)

| Idea | Why not (for v1 / as the spine) |
|---|---|
| **Static 1 FPS whole video into Gemma** | Cost scales with duration; Gemma 4 ~60s video gulp; misses sub-second events unless FPS is high everywhere |
| **New video foundation model** | Google didn’t ship one; they shipped a **tool loop** |
| **Whisper describes scenes / slides** | Whisper has **no eyes** |
| **VLM caption every few seconds (`search_notes`)** | Thousands of LLM calls at ingest; we already have specialists + Gemma at query time |
| **Answer only from the index** | Captions and embeddings lie; Google still **opens frames** |
| **PySceneDetect as core** | Finds **cuts**, not “red light” or “bird.” Optional later to skip duplicate lecture slides |
| **OpenAI CLIP as the visual encoder** | Works as a tutorial; **SigLIP 2** is the stronger default (Apache-2.0) |
| **Pixel CLIP as the only visual story** | Doesn’t **read** “Pro $99”; that’s Gemma on frames after a time is known |
| **OCR every frame at ingest** | Expensive; OCR **one** fetched frame later if the brain misreads slides |
| **No visual index, Gemma skims 2h** | Correct Google-like logic, **slow/$** on long CCTV every question |
| **No audio index** | Cannot do “bird chirp” / claps without chewing hours of audio in Gemma |
| **Clap-only detector as the audio design** | Too narrow; **`search_audio`** covers chirps, beeps, claps; detector only if counting ovations fails |
| **Train Gemma E2B as CLIP/CLAP** | Possible on Modal with data; **worse efficiency**. Fine-tune **CLAP** on domain data first |
| **MediaBunny as the backend cutter** | Fine in **browser**; server path is still FFmpeg. **ffmpeg CLI** for v1 |
| **Node as the ML API** | Whisper/SigLIP/Gemma live in **Python**. FastAPI is the API. (An earlier PR tried Node-on-laptop. Not this app.) |
| **Native Gemma `tools=` / OpenAI function calling** | Tool messages often drop image/audio. E4B is weak at multi-step tools. We own JSON + multimodal parts. |
| **Gemma 12B as the default brain** | We own the loop, so E4B is enough. 12B is an env switch later. |
| **SQLite + FAISS as the store** | One **Postgres + pgvector** for rows, keyword search, and vectors. |
| **Vite SPA / Next.js as the UI kit** | **TanStack Start** + shadcn + Query. Browser still talks only to FastAPI. |
| **WhisperX + three-speed form driver + Node API** | Other draft PRs. Not merged. Speech is faster-whisper turbo + hybrid FTS/E5. API is FastAPI. |
| **ColQwen as a v1 index** | Fourth book for on-screen text. **Not v1.** Design kept below so we can add it later if slides fail. |
| **Gemma audio instead of Whisper for the full file** | Gemma audio ~**30s**; 2h lecture needs Whisper cache |
| **31B / 26B-A4B as the omni brain** | **No native audio** on those sizes |
| **Kitchen-sink desktop tools** (web, python, calendar) | Different product. Video loop first |
| **Full Agentic Vision (arbitrary Python on images)** | `crop_frame` is enough if tiny objects fail |
| **Graph DB / Elasticsearch on day one** | Postgres + pgvector is enough |

---

# Alternative: ColQwen / `search_slides` (not v1)

This is the slide-search design from the closed [PR #2](https://github.com/omnaiduu/agentic-video-understanding/pull/2) branch. **Do not build it in phases 1–12.** SigLIP 2 stays the picture book. Keep this page so a later agent can add a fourth book if talks fail on printed text.

**v1:** Whisper + SigLIP 2 + CLAP + Gemma on short slices.  
**This alternative:** same loop, plus unique-slide dedup and ColQwen so “which slide had **Pro $99**?” can find a time when nobody **said** the number.

Gemma still **reads** the real frame. ColQwen only **finds the second**.

## Why it exists

Talks are a first-class use case. Two different questions:

- “What did she **say** about pricing?” → Whisper `search`. Fine.
- “Which slide had **Pro $99**?” and she never said “ninety-nine.”

| Tool (v1) | What it does | Why it misses `$99` |
|---|---|---|
| `search` | Spoken words | Number never spoken |
| `search_visual` (SigLIP) | One vector for the **whole** photo | Tiny text is drowned; every slide “looks like a slide” |
| `look` + Gemma | **Reads** the slide | Only if we already know the time |

The gap is the **finder**, not the reader. Do not OCR every frame. Do not caption every second. Add a **slide map**, then the same loop: find time → `look` → Gemma answers.

## Two problems (do not mix them)

### 1 — too many copies of the same slide

At **1 FPS**, a 40-minute deck with **40 slides** is ~**2,400 photos**. Slide 7 stays up for a minute → 60 almost-identical frames. Search gets muddy.

**Fix: dedup.** If this frame is almost the same as the last **kept** frame, don’t store another copy. Keep **one image + a time span** (`12:04–12:58`).

That is **not** PySceneDetect. Scene detect finds **movie cuts**. A lecture can change slides with **no cut**, or cut the camera while the slide stays. Compare **pixels of the screen**, not edits.

**How:** perceptual hash (pHash) on the frame or the slide region; or SigLIP cosine vs last kept frame (very high similarity = same slide). Optional: hash the deck area, ignore a talking-head strip.

**When it helps:** static pictures — slides, shared PDF, talking-head with the same wall. **Sports / motion:** almost every frame is different; little savings. **CCTV empty hallway:** saves copies, but the threshold must not drop the one second a person appears.

Dedup does **not** read `$99`. It only makes the picture book smaller. ColQwen should run on **unique slides**, not on 2,400 frames. Dedup still helps SigLIP even if ColQwen never ships.

### 2 — CLIP / SigLIP cannot read the slide

SigLIP is the right tool for **objects and scenes**. It is the wrong tool for **a specific string on a busy slide**.

**Fix: ColQwen (ColPali family)** on those **unique** slides. Search like visual **PDF RAG**: match query words to **patches** of the page. Then Gemma still opens that timestamp and reads.

This **is** slideshow RAG. In this product it would be one extra search tool, not a new app.

## When this is useful (and when it is not)

Use it when the question is about **what is printed on screen**, and speech + SigLIP both miss it.

Helps:

- “Which slide had **Pro $99**?”
- “When did they show the diagram with **KV cache**?”
- “Find the table with **Q3 revenue**.”
- Zoom **shared PDF**, tutorial **IDE / terminal / error text**

Does **not** replace:

| User asks | Use |
|---|---|
| “What did she say about pricing?” | Whisper / `search` |
| “Flying bird / red light / yellow jacket” | SigLIP / `search_visual` |
| “When did people clap?” | CLAP / `search_audio` |
| “Summarize the talk” | Transcript (+ a bit of video) |
| Already know the time | `look` — Gemma reads; skip ColQwen |

Scorebugs, license plates, tiny TV overlays: same *idea*, weaker fit (these models were trained on **pages**). Not the main win.

## The extra tool

Name: **`search_slides`**. Same job as the other `search_*` tools: **return times**. Not answers.

```
upload
  → ffmpeg ~1 FPS
  → unique slides + time ranges
  → SigLIP on frames (or uniques)     search_visual   bird / red light
  → ColQwen on unique slides only     search_slides   “Pro $99”
  → look(t) → Gemma reads
```

| Tool | Input | Output | Role |
|---|---|---|---|
| `search_slides` | phrase | `[{t, score, slide_id}]` | Find **which unique slide** matches on-screen text/layout |
| `look` | start, end, fps | images to Gemma | **Read** — unchanged |

v1 tools in [06-tools.md](06-tools.md) stay as they are. ColQwen **finds**; optional `ocr_frame` is a last-ditch **read** of **one** already-opened frame. Prefer not to OCR the whole video.

## How ColQwen works

**ColPali** (ICLR 2025, PaliGemma) invented the recipe. **ColQwen / ColQwen2 / ColQwen2.5** is the same idea on **Qwen2-VL / Qwen2.5-VL**. Default if we ever ship this: **ColQwen2.x** — stronger on small fonts, dense slides, more languages. ColPali is the ancestor, not the 2026 default.

They are **retrievers**, not chatbots.

1. **A slide is a grid of patches**, not one vector. Each patch might be a word, a bar in a chart, a table cell.
2. Vision encoder + language model → each patch becomes a **short** vector (ColBERT-style, ~128-d). One slide → hundreds of vectors. SigLIP: **one** vector for the whole photo.
3. The **query** is text only: one vector per token (`Pro`, `$`, `99`, …).
4. **Late interaction (MaxSim):** for each query token, take the **best** matching patch, then **sum**. Token `99` can lock onto the `$99` patch even if most of the slide is a speaker photo.
5. **Trained as retrieval** (this question ↔ this page), not as OCR (emit a string). Gemma still does QA on the chosen frame.

**Why not run it on every second of video:** hundreds of vectors per page × 2,400 frames is huge. After dedup, ~40 slides × MaxSim is cheap. Fancy ANN (Qdrant/Vespa two-stage) is for **libraries of PDFs**, not one lecture.

## Models — if we add this later

| Piece | Choice | Why |
|---|---|---|
| Scene / object search | **SigLIP 2** (keep) | Still the visual index for bird, red light, people |
| Collapse duplicate frames | **pHash and/or SigLIP vs previous** | Problem 1. Not scene detect |
| On-screen text / slide search | **ColQwen2.x** | ColPali recipe, better eyes for dense text |
| Fallback if ColQwen is painful | **ColPali** | Original, PaliGemma; slightly weaker on small fonts |
| Reader | **Gemma 4** on `look` | Locked brain. Answers from rewatch, not from search scores |
| Last-ditch read | optional `ocr_frame` | One fetched frame, not ingest |

SigLIP and ColQwen **both** can exist. Different questions. Do not replace `search_visual` with ColQwen.

## Why not the tempting shortcuts

| Tempting idea | Why not |
|---|---|
| Let Gemma skim 2h of slides | Slow/$; ~60s video gulp |
| Caption every slide with a VLM at ingest | Thousands of LLM calls; already refused |
| OCR every frame | Brittle, expensive; ColQwen **skips** OCR for **finding** |
| Answer from ColQwen scores only | Embeddings lie; Google still opens frames |
| Scene detect as the slide finder | Cuts ≠ new slide |
| One SigLIP vector but “try harder” | Cannot attend to a tiny `$99` patch the way MaxSim can |

## If we ever build it (after v1)

1. Ship phases 1–12 first. Prove talk / bird / clap.
2. **Dedup unique frames** at ingest. Helps SigLIP even before ColQwen.
3. If “what’s on the slide?” fails in real use: **ColQwen on uniques** + `search_slides` + same `look`.
4. Only if Gemma still misreads a dense slide: `ocr_frame` on that one frame.

Done for *this* slice when: a lecture answers “which slide had [text nobody spoke]?” with a timestamp, without loading the whole video into Gemma, and without OCR-all-frames.
