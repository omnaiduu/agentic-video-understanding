# Frontend and backend

Locked with the 13 phases.

## Backend

| Piece | Choice | Why |
|---|---|---|
| Language | **Python 3.11+** | Whisper, SigLIP, CLAP, ColQwen, Gemma clients |
| HTTP | **FastAPI** | Upload, ingest jobs, chat |
| ORM / DB | **SQLModel + PostgreSQL + pgvector** | Rows, FTS, vectors, sessions |
| Media | **ffmpeg** CLI | Cut frames/audio/clips |
| Agent | vLLM OpenAI client, **`response_format` JSON schema**, no `tools=` | Phase 3 |
| Ingest | Same `ingest_video(id)` — BackgroundTasks on laptop, Modal `.spawn()` later | Doc 13 still open on *where* |
| Auth | None | v1 |
| Files | Local disk `data/videos/{id}/` | S3 later behind the same functions |

### API sketch

- `POST /videos` — multipart upload **or** JSON path; copy + ffprobe; start ingest
- `GET /videos` — library
- `GET /videos/{id}` — metadata + overall status + per-index statuses
- `GET /videos/{id}/file` — original bytes, **Range**
- `DELETE /videos/{id}` — row + folder + sessions + exports
- `POST /videos/{id}/chat` — `{ message, session_id? }` → `{ answer, citations, steps, session_id, export_url? }`
- `GET /videos/{id}/exports/{export_id}` — clip/audio, Range

### Status

Overall: `uploaded` → `processing` (ingest) → `ready` | `error`.  
Books: `transcript_status` / `visual_status` / `audio_status` / `slides_status` = pending | processing | ready | error | skipped.  
Website polls overall status; **chat stays off until `ready`.**

### Session

`session_id` on chat. Last **3** time windows as **text**. Omit id → new thread. Refresh keeps the same id (localStorage on the watch page).

## Frontend

**Job:** library, upload with progress, player, chat, click-to-seek, clip **in the chat bubble**, phone stack, delete.

| Piece | Locked |
|---|---|
| App | **TanStack Start** in `web/` (React + Vite + file routes) |
| Style | Tailwind + **shadcn/ui** |
| Data | **TanStack Query** (`useQuery` / mutations / `refetchInterval`) |
| Player | **Video.js** on FastAPI file URL + Range |
| Routes | `/` library+upload, `/videos/$videoId` watch+ask |
| ML | **Never** in Start server functions |

Screens: empty library → upload → processing → watch+ask → clip in thread. API down → error, no crash. Phone: player above, chat below (~768px).

## Not this stack

- Next.js as the API
- Node/Go cutting media
- MediaBunny as the backend cutter
- SQLite / FAISS
- Login / signed URLs in v1

## Resources / throughput (honest ranges)

- E4B 4-bit on an L4: comfortable for this loop.
- Typical **search + frames + 2–4 rounds** often **~10–40s**, GPU-bound.
- pgvector / CLAP query: milliseconds.
- ffmpeg 5s export: sub-second to a few seconds.
- Bottleneck = **Gemma + frames**, not Postgres.

Hosting *where* (laptop vs Modal) is the remaining open talk in [13](13-implementation-pass.md).
