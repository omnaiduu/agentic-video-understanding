# Frontend and backend

Frontend was **not** locked in the earlier thread. This is the plan that fits the decisions.

## Backend

**Demo stack (what we run locally):** Node on the laptop is the API. Models stay on **Modal** in Python. Detail and algorithms: [20-backend-algorithm.md](20-backend-algorithm.md).

| Piece | Choice | Why |
|---|---|---|
| Product API | **Node** (local) | You asked for Node for the demo; HTTP, SQLite, ffmpeg, calls Modal |
| ML | **Python on Modal** | Whisper, SigLIP, CLAP/GLAP, Gemma cannot run in Node |
| HTTP | Node `/videos` + `/chat` | Upload, ingest status, questions |
| Media | **ffmpeg** CLI on the laptop | Cut frames/audio/clips |
| Brain | OpenAI-compatible calls to **Modal** Gemma E4B | Two calls: **plan** (form) and **answer** (short slice) |
| Ingest workers | Modal jobs | WhisperX/SigLIP/GLAP once |
| Auth | None for local v1 | Add later |

Main Gemma sees **last ~8 user messages** (what they typed) **plus the notepad** (the clock, e.g. 1:04). User text alone cannot fill times.

### API sketch (v1)

- `POST /videos` — upload or register path; start ingest
- `GET /videos/{id}` — status: processing | ready | error
- `POST /videos/{id}/chat` — message; returns answer, citations `{t}`, verb trace, export URLs
- `GET /videos/{id}/exports/{file}` — or public object-storage URLs

### Data

| Store | Holds |
|---|---|
| **SQLite** | video rows, transcript lines (FTS), chat sessions, last timestamps |
| **FAISS or sqlite-vec** | SigLIP + CLAP vectors + time |
| **Object storage** | original mp4, exported clips/audio |

Postgres + pgvector when there are many users/videos — not day one.

### Session

Persist a **clipboard** per chat: `handle_id`, **focus** window `{t0,t1}`, last search hits (talk/look/listen), one-line notes. Follow-up “was a car in that frame?” uses focus — no re-search. Combo questions update focus in order (`shift_after`). See [16-clipboard-and-verbs.md](16-clipboard-and-verbs.md).

## Frontend

**Job:** upload (or pick a file), show ingest progress, chat, show timestamps (click to seek), show exported clip/audio links, empty/error/loading states.

**Proposed v1 demo UI:** one **watch + ask** page (upload, status, chat, timestamp chips, clip link). Vite + React if we want; a single static page is enough to record. Not a second ML stack.

Why not Next.js as a must: we never chose it; a SPA against FastAPI is enough. Swap later if we need SSR.

Screens:

1. Library — videos, ingest status
2. Watch + ask — player, thread, timestamp chips, “download clip”
3. Empty: no video yet
4. Error: ingest failed / model down

Desktop + mobile: player + chat stack on small screens.

## ffmpeg vs MediaBunny vs Node vs Go

- **ffmpeg:** backend cutter. Locked.
- **MediaBunny:** browser trim/preview later; not the ML path.
- **Node:** **demo API** (orchestrator). Not the ML worker.
- **Go:** later high-QPS cut service; not v1.

## Local vs Modal

- **Dev / demo:** Node + ffmpeg + SQLite on the laptop; Gemma + ingest on **Modal**. Record a screen video when the checks in [20](20-backend-algorithm.md) pass.
- **Prod (later):** same split, or move the Node API next to Modal; files on Volume/S3.

## Resources / throughput (honest ranges)

- E4B 4-bit: more concurrent chats on one L4.
- 12B 4-bit: typical **search + 20 frames + 2–4 tool rounds** often **~10–40s**, GPU-bound.
- FAISS/CLAP query: milliseconds.
- ffmpeg 5s export: sub-second to a few seconds.
- Bottleneck = **Gemma + frames**, not SQLite.
