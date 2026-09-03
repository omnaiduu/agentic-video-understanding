# Frontend and backend

Frontend was **not** locked in the earlier thread. This is the plan that fits the decisions.

## Backend

| Piece | Choice | Why |
|---|---|---|
| Language | **Python 3.11+** | Whisper, SigLIP, CLAP, Gemma clients |
| HTTP | **FastAPI** | Async jobs (ingest) + chat |
| Media | **ffmpeg** CLI | Cut frames/audio/clips; codecs just work |
| Agent | OpenAI-compatible calls to **Modal**-hosted Gemma (tool calling) | User hosts models there |
| Ingest workers | Modal jobs or FastAPI background + queue | Whisper/SigLIP/CLAP once |
| Auth | None for local v1 | Add later |

### API sketch (v1)

- `POST /videos` — upload or register path; start ingest
- `GET /videos/{id}` — status: processing | ready | error
- `POST /videos/{id}/chat` — message; returns answer, citations `{t}`, tool trace, export URLs
- `GET /videos/{id}/exports/{file}` — or public object-storage URLs

### Data

| Store | Holds |
|---|---|
| **SQLite** | video rows, transcript lines (FTS), chat sessions, last timestamps |
| **FAISS or sqlite-vec** | SigLIP + CLAP vectors + time |
| **Object storage** | original mp4, exported clips/audio |

Postgres + pgvector when there are many users/videos — not day one.

### Session

Persist `handle_id` (which video + indexes) and last tool times so “was a car in that frame?” does not re-search the whole tape.

## Frontend

**Job:** upload (or pick a file), show ingest progress, chat, show timestamps (click to seek), show exported clip/audio links, empty/error/loading states.

**Proposed v1:** **Vite + React + TypeScript**, talks to FastAPI. Not a second ML stack.

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
- **Node:** optional BFF; not required.
- **Go:** later high-QPS cut service; not v1.

## Local vs Modal

- **Dev:** Ollama or vLLM on a GPU box; local ffmpeg; SQLite on disk.
- **Prod:** Gemma + ingest on **Modal**; API can stay on Modal too; files on Volume/S3.

## Resources / throughput (honest ranges)

- E4B 4-bit: more concurrent chats on one L4.
- 12B 4-bit: typical **search + 20 frames + 2–4 tool rounds** often **~10–40s**, GPU-bound.
- FAISS/CLAP query: milliseconds.
- ffmpeg 5s export: sub-second to a few seconds.
- Bottleneck = **Gemma + frames**, not SQLite.
