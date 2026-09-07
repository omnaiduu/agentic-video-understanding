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
| 8 | Memory | Multi-turn last timestamps | **LOCKED** — [phase-08.md](phases/phase-08.md) |
| 9 | UI shell | TanStack Start + shadcn + Query | **LOCKED** — [phase-09.md](phases/phase-09.md) |
| 10 | Upload UI | Pick file, ingest progress | **LOCKED** — [phase-10.md](phases/phase-10.md) |
| 11 | Watch + ask | Video.js, chat, seek, collapsed trace | **LOCKED** — [phase-11.md](phases/phase-11.md) |
| 12 | Clips + polish | Clip in chat, phone stack, delete, README | **LOCKED** — [phase-12.md](phases/phase-12.md) |

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

**LOCKED.** Brief: [phases/phase-08.md](phases/phase-08.md)

Last 3 time windows; `session_id`; text pointers, not old photos. Last backend slice.

---

# Phase 9 — UI shell

**LOCKED.** Brief: [phases/phase-09.md](phases/phase-09.md)

TanStack Start + shadcn/Tailwind + TanStack Query. Library + watch+ask shell. FastAPI stays the API.

---

# Phase 10 — Upload UI

**LOCKED.** Brief: [phases/phase-10.md](phases/phase-10.md)

File picker on the library; byte progress; Query poll; jump to `/videos/:id`.

---

# Phase 11 — Watch + ask

**LOCKED.** Brief: [phases/phase-11.md](phases/phase-11.md)

Video.js; saved `session_id`; click-to-seek; Working…; collapsed tool trace. No export buttons yet.

---

# Phase 12 — Clips + polish

**LOCKED.** Brief: [phases/phase-12.md](phases/phase-12.md)

Exported clip lives **in the scrollable chat**. Phone stacks player above chat. Delete button. Root README.

**All 12 phases are locked.** An agent implements one brief at a time, in order, toward one production app.

---

# Rules for every phase

1. Same repo. Same video id. Same tools module. Grow it; do not start a second app.
2. Indexes are caches. The product is the agent loop.
3. Counting is code on hits, not Gemma memory.
4. If something is **OPEN**, ask the human. Do not invent a second product.
