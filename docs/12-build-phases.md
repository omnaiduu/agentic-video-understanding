# Build phases (complete app)

This is **one production app**, built in slices. It is not a v1 toy that we later replace.

Old docs stay. They are the *why* and the *locked product*. This file is the *build order* for an AI agent.

| Read this | For |
|---|---|
| [01 Goal](01-goal-and-context.md) | What the product is |
| [03 Key decisions](03-key-decisions.md) | Locked product choices |
| [05 Architecture](05-architecture.md) | Ingest vs question loop |
| [06 Tools](06-tools.md) | Tool list and caps |
| [07 Models](07-models-and-indexes.md) | Gemma, Whisper, SigLIP, CLAP |
| [08 Frontend/backend](08-frontend-backend.md) | Stack |
| [09 Implementation plan](09-implementation-plan.md) | Original build order (this file replaces it as the agent brief) |
| [11 Glossary](11-glossary.md) | Words |

**How an agent should use this file**

- Do **only** the phase you were told to do.
- Do not skip ahead (no Whisper in Phase 1, no React in Phase 3).
- Leave seams for later phases (folder layout, status field, tool module). Do not implement those later phases.
- When a phase says **LOCKED**, follow it. When it says **OPEN**, stop and ask the human.

**End state (the complete app)**

Upload a long video → indexes built once (speech, pictures, sounds) → ask questions → Gemma uses tools on short slices → timestamped answer → optional clip link → website for upload, player, chat. Second question does not re-ingest.

Backend first (Phases 1–8). Frontend second (Phases 9–12). Same app.

---

## Phase map

| Phase | Name | Adds to the app | Status |
|---|---|---|---|
| 1 | Hold a video | FastAPI + SQLite + save file + duration | **LOCKED** — [phase-01.md](phases/phase-01.md) |
| 2 | Scissors | `get_meta` / `get_frames` / `get_audio` + caps | **LOCKED** — [phase-02.md](phases/phase-02.md) |
| 3 | Brain loop | Gemma calls those tools, `/chat` | **LOCKED** — [phase-03.md](phases/phase-03.md) |
| 4 | Speech index | Hybrid Whisper RAG on **Postgres** | **LOCKED** — [phase-04.md](phases/phase-04.md) |
| 5 | Picture index | SigLIP 2 + `search_visual` | Proposed |
| 6 | Sound index | CLAP/GLAP + `search_audio` + count | Proposed |
| 7 | Export | `export_clip` / `export_audio` + URL | Proposed |
| 8 | Memory | Multi-turn last timestamps | Proposed |
| 9 | UI shell | React app, pages, empty/loading/error | Proposed |
| 10 | Upload UI | Pick file, ingest progress | Proposed |
| 11 | Watch + ask | Player, chat, seek on timestamps | Proposed |
| 12 | Clips + polish | Download links, mobile, errors | Proposed |

---

# Phase 1 — Hold a video

**LOCKED.** Brief: [phases/phase-01.md](phases/phase-01.md)

---

# Phase 2 — Scissors

**LOCKED.** Brief: [phases/phase-02.md](phases/phase-02.md)

---

# Phase 3 — Brain loop

**LOCKED.** Brief: [phases/phase-03.md](phases/phase-03.md)

vLLM JSON schema + our look/listen/answer state machine. Not native `tools=`.

---

# Phase 4 — Speech index

**LOCKED.** Brief: [phases/phase-04.md](phases/phase-04.md)

Hybrid keyword + dense RAG on Whisper lines. PostgreSQL + pgvector (not SQLite).

---

# Phase 5 — Picture index

**In one sentence:** ~1 photo per second → **SigLIP 2** vectors; `search_visual("red light")` returns times.

## What it is doing

Whisper has no eyes. This is the picture phone book ([07](07-models-and-indexes.md)). Still not the answer: Gemma must `get_frames` to verify.

Ingest: ffmpeg 1 FPS → SigLIP → vectors + times, next to the video id.

## Plan

1. Frame sample at 1 FPS (ffmpeg), encode, discard bulk JPEGs after vectors are stored (keep vectors + times).
2. Vector table or sqlite-vec / FAISS file per video or one index with video_id.
3. Tool `search_visual(phrase)`: embed phrase, nearest times.
4. Register tool.

## Libraries

| Piece | Proposed | Option |
|---|---|---|
| Encoder | **SigLIP 2** (Hugging Face / timm) | not 2021 OpenAI CLIP ([04](04-what-we-rejected.md)) |
| Vectors | **sqlite-vec** | FAISS — faster at huge scale, extra file |
| Query | embed text with same SigLIP text tower | |

## Technical decisions (lock later)

- sqlite-vec vs FAISS.
- Keep sampled frames on disk or not (storage vs easier debug). **Proposed: delete JPEGs after embed**; ffmpeg can recreate any time.

## Done when

Silent visual query returns a timestamp without Gemma scanning 2 hours.

---

# Phase 6 — Sound index

**In one sentence:** 1–5s audio chunks → **CLAP/GLAP** vectors; `search_audio("chirp")`; counts happen in **Python**, not in Gemma’s head.

## What it is doing

Picture index will not hear a bird. Whisper will not write “clap.” Same pattern as SigLIP ([05](05-architecture.md) counting section).

```
search_audio → times → merge nearby hits → len() in code
→ optional get_audio on 2–3 samples to verify
```

Stadium applause may be one blob. Honest answer: “applause 1:00–1:40”, not a fake 847.

## Plan

1. Chunk audio 1–5s, embed, store vectors + times.
2. `search_audio(phrase)`.
3. Optional helper `count_events` later ([06](06-tools.md)); for this phase, merge+count in the tool or in Python the agent is instructed to trust.
4. Register tool.

## Libraries

| Piece | Proposed | Option |
|---|---|---|
| Encoder | **LAION-CLAP** | **GLAP** (newer, same tool API) |
| Chunk | 3s default, 1s hop or 3s hop | 1s vs 5s |
| Vectors | same store as visual (sqlite-vec / FAISS) | |

## Technical decisions (lock later)

- CLAP vs GLAP.
- Clap-only detector: **not** this phase ([04](04-what-we-rejected.md)).

## Done when

“When did the bird make a sound?” returns a time from the audio index; Gemma may confirm with `get_audio`.

---

# Phase 7 — Export

**In one sentence:** after times are known, cut a clip or audio file, save it, return an **HTTPS (or local) URL**. Cap length (e.g. 60s).

## What it is doing

Find / understand / **give the user a file** — third job ([05](05-architecture.md)).

Tools: `export_clip(start, end)`, `export_audio(start, end)`.

## Plan

1. ffmpeg write `data/videos/{id}/exports/{export_id}.mp4` (or wav).
2. `GET /videos/{id}/exports/{export_id}` streams the file (Phase 1 local disk). Object storage (S3/R2/Modal Volume) later **behind the same storage interface**.
3. Register tools; duration cap.
4. Chat response can include `export_url`.

## Libraries

- ffmpeg CLI again.
- No new web framework.

## Technical decisions (lock later)

| Topic | Proposed | Option |
|---|---|---|
| Where files live | Local disk + API GET | S3/R2/Modal Volume when we host |
| Max length | 60s | config |
| Auth on URLs | none for now | signed URLs when we add users |

## Done when

Tool returns a URL; fetching it is a playable short mp4/wav; 10-minute request is rejected.

---

# Phase 8 — Memory (multi-turn)

**In one sentence:** follow-up uses the **same video** and **last times** (“was a car in that frame?”) without re-ingest and without searching the whole tape again.

## What it is doing

Google’s `step_list` idea ([02](02-conversation-summary.md)): persist `handle_id` (video + indexes) and last tool timestamps.

## Plan

1. `Session` / `ChatMessage` (if not already from Phase 3).
2. `last_times: list[{start, end, kind}]` on the session.
3. System prompt: prefer last times for “that frame / there / the clip”.
4. `POST /videos/{id}/chat` takes optional `session_id`.

## Libraries

- Same SQLite. No Redis required.

## Technical decisions (lock later)

- How many last windows to keep (e.g. last 3).
- Optional `crop_frame` / `ocr_frame` are **not** this phase ([06](06-tools.md) later list).

## Done when

Two-turn test: find a moment, then a follow-up about “that” moment does not re-run ingest and does not search from scratch if times exist.

---

# Phase 9 — UI shell

**In one sentence:** a website exists with the right screens, talking to the API, even if upload/chat are still wired crudely.

**Depends on:** backend Phases 1–8 already serving HTTP.

## What it is doing

[08](08-frontend-backend.md): library, watch+ask, empty, error, loading. Desktop + mobile stack (player then chat on small screens).

## Plan

1. `web/` Vite + React + TypeScript.
2. React Router: `/` library, `/videos/:id` watch+ask.
3. API client (`VITE_API_URL`).
4. Empty / loading / error components. Library can list `GET /videos`.
5. No need for a design system. Simple CSS (see options).

## Libraries

| Piece | Proposed | Option |
|---|---|---|
| App | **Vite + React + TS** | Next.js — not required ([08](08-frontend-backend.md)) |
| Routing | **react-router** | |
| Style | **plain CSS** or **CSS modules** | Tailwind |
| Player | later (Phase 11) | |

## Technical decisions (lock later)

- CSS vs Tailwind.
- Whether library is usable with videos created only via API/curl (yes).

## Done when

Open `/`, see empty or a list from the API. Navigate to a video page shell. No crash if API is down (error state).

---

# Phase 10 — Upload UI

**In one sentence:** pick a file in the browser, see **processing → ready** (or error).

## What it is doing

`POST /videos` multipart + poll `GET /videos/{id}`. This is why Phase 1 upload exists.

## Plan

1. File input, upload progress (bytes).
2. Poll status until `ready` or `error`.
3. Show ingest failure message.

## Libraries

- Same React app. `fetch` or a thin wrapper. No extra upload SDK.

## Done when

Upload a short mp4 in the UI; status becomes ready; it appears in the library.

---

# Phase 11 — Watch + ask

**In one sentence:** play the video, type a question, see the answer, click a **timestamp** to seek.

## What it is doing

The human loop: watch and ask. Player uses `GET` of the original (need a media route if files are not public — add `GET /videos/{id}/media` if missing).

## Plan

1. HTML5 `<video>` (simple).
2. Chat panel: messages, input, waiting state.
3. `POST /videos/{id}/chat`.
4. Timestamp chips → `video.currentTime = t`.
5. Optional: show tool_trace behind a “details” disclosure (debug, not required).

## Libraries

| Piece | Proposed | Option |
|---|---|---|
| Player | native `<video>` | video.js / Media Chrome later |
| Media URL | FastAPI streams `original.mp4` | |

## Done when

Ask a question on a ready video; see answer text; click a time; player jumps there.

---

# Phase 12 — Clips + polish

**In one sentence:** show **clip/audio links** from export tools; layout works on a phone; ingest/model-down errors are readable.

## What it is doing

Finish the complete app, not a new product.

- Render `export_url` as download / inline play.
- Stack player + chat on small width.
- Copy for: no video, ingest error, model unreachable.
- README at repo root: how to run backend + web.

## Not in this phase (still later / never)

- Login, Postgres, Elasticsearch.
- `search_notes`, scene detect, train E2B as CLIP ([04](04-what-we-rejected.md)).
- `crop_frame` / `ocr_frame` unless we already failed on tiny objects / slides.
- Kitchen-sink desktop agent.

## Done when (complete app)

A ≥10 minute video can: (a) speech question, (b) silent visual, (c) sound question, (d) follow-up without re-ingest, (e) exported clip URL, (f) all of that from the website — without loading the whole file into Gemma. Same bar as [09](09-implementation-plan.md), plus UI.

---

# Rules for every phase

1. Same repo. Same video id. Same tools module. Grow it; do not start a second app.
2. Indexes are caches. The product is the agent loop.
3. Counting is code on hits, not Gemma memory.
4. If something is **OPEN**, ask the human. Do not invent a second product.
