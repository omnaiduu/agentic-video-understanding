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
| 1 | Hold a video | FastAPI + Postgres + save file + duration | **LOCKED** — [phase-01.md](phases/phase-01.md) |
| 2 | Scissors | `get_meta` / `get_frames` / `get_audio` + caps | **LOCKED** — [phase-02.md](phases/phase-02.md) |
| 3 | Brain loop | Gemma JSON loop, `/chat` | **LOCKED** — [phase-03.md](phases/phase-03.md) |
| 4 | Speech index | Hybrid Whisper RAG on **Postgres** | **LOCKED** — [phase-04.md](phases/phase-04.md) |
| 5 | Picture index | SigLIP 2 + `search_visual` | **LOCKED** — [phase-05.md](phases/phase-05.md) |
| 6 | Sound index | CLAP + `search_audio` + Python count | **LOCKED** — [phase-06.md](phases/phase-06.md) |
| 7 | Export | `export_clip` / `export_audio` + URL | **LOCKED** — [phase-07.md](phases/phase-07.md) |
| 8 | Memory | Multi-turn last timestamps | **OPEN** — [phase-08.md](phases/phase-08.md) |
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

**LOCKED.** Brief: [phases/phase-05.md](phases/phase-05.md)

SigLIP 2 at ~1 FPS → pgvector; `search_visual` in the JSON loop. Dense picture search (not hybrid).

---

# Phase 6 — Sound index

**LOCKED.** Brief: [phases/phase-06.md](phases/phase-06.md)

LAION-CLAP on 3s chunks → pgvector; `search_audio` in the JSON loop. Counts happen in **Python**.

---

# Phase 7 — Export

**LOCKED.** Brief: [phases/phase-07.md](phases/phase-07.md)

60s cap, reject oversize; local GET URL; mp4 / wav; re-encode; `export_clip` / `export_audio` in the JSON loop.

---

# Phase 8 — Memory (multi-turn)

Full brief: **[phases/phase-08.md](phases/phase-08.md)**

Do not implement from this map. Status: not locked until the human answers the questions there.

Follow-up uses the same video and last times. No re-ingest. No Redis.

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
