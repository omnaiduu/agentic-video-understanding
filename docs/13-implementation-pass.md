# Implementation pass — how, not what

**Status: LOCKED.** Product phases 1–13 stay locked. This file is the **how**: where it runs, which GPU, how ingest starts, how small the code stays. **Phase 1 how-to card** is also locked (uv, Docker Postgres, Alembic, chunked upload).

A coding agent follows the phase brief **and** that phase’s card below. Do **not** implement the whole app. One phase at a time, starting at [Phase 1](phases/phase-01.md).

Related: [phase map](12-build-phases.md) · [hosting](08-frontend-backend.md) · [models](07-models-and-indexes.md) · [method](14-from-idea-to-production.md)

---

## What you already locked (do not reopen)

| Piece | Locked |
|---|---|
| API | FastAPI + SQLModel + **Postgres** + pgvector |
| Cut | ffmpeg CLI, 64 photos / 30s audio, 60s export |
| Brain | Gemma 4 **E4B** default, vLLM **JSON schema**, our state machine |
| Speech | faster-whisper turbo, hybrid FTS + E5 |
| Pictures | SigLIP 2 `so400m-patch16-384` |
| Slides | ColQwen2.x on unique frames; `search_slides` |
| Sound | LAION-CLAP, 3s / 1.5s hop |
| UI | TanStack Start, shadcn, Tailwind, TanStack Query, Video.js |
| Files | Laptop disk `data/videos/{id}/` (S3 later behind the same functions) |
| Phase 1 how | Card below |

---

## Hosting (locked this pass)

**This is the real setup, not a throwaway.**

| Job | Where | GPU |
|---|---|---|
| Website + FastAPI + Postgres + ffmpeg (scissors) | **Your laptop** | none |
| Chat brain (Gemma via vLLM) | **Modal**, own worker | **L4** (24 GB). A10 only if L4 is unavailable. Not A100. |
| Ingest (Whisper, SigLIP, CLAP, ColQwen) | **Modal**, **different worker** from chat | **L4**. A10 if one book does not fit. Not A100. |

**$30 Modal credit** is enough for this shape (L4 ≈ $0.80/hr, billed per second, idle ≈ $0). Do not keep a GPU warm.

**Two workers, not two products.** Chat and ingest never share one running GPU replica. Same *type* of card is fine. Ingest runs the four books **in order** on that ingest worker (speech → pictures → sounds → slides) so we do not pay two GPUs at once unless chat is asked during ingest.

**Modal only gets slices.** The video file stays on the laptop. Laptop ffmpeg cuts audio/frames. Modal receives those pieces, returns transcript / vectors / Gemma JSON, and does not keep the full file.

**How ingest starts:** laptop FastAPI calls Modal `.spawn()` on `ingest_video(id)`. Same Python ingest function. Not Whisper on the laptop. Not Redis/Celery.

**Laptop-only Phase 1–2:** no Modal yet. FakeBrain in tests. First Modal call is Phase 3 (Gemma) and Phase 4 (Whisper).

**Scale to zero.** After a job, the GPU shuts off.

---

## Size (locked)

- A handful of new files per phase, about **200–300 lines** each. Split if bigger.
- **No new library** that is not on the phase card. Stop and ask.
- FakeBrain / mock Query in tests. **No GPU in CI.**
- Do **not** put Whisper / SigLIP / CLAP / ColQwen / Gemma in TanStack Start server functions.

---

## Live ingest on the website (locked)

While a video is indexing, the UI must show **what is being built**, not a silent wait.

- After the file **finishes uploading**, go to `/videos/:id` even if status is still `processing`.
- Spinner + four lines, updated by polling `GET /videos/{id}`:
  - Speech index
  - Picture index
  - Sound index
  - Slide index
- Each line: waiting / building / ready / skipped / error.
- Chat stays **off** until overall `ready`.
- Library row may say “Indexing…”; the four-line list lives on the video page.

Backend already has `transcript_status` · `visual_status` · `audio_status` · `slides_status`. UI must **show** them live. Phase 10 builds this panel; Phase 11 keeps it while chat is off.

---

## Phase 1 card — **LOCKED** (how to write it)

Product brief stays [phase-01.md](phases/phase-01.md). An agent follows **this card** plus that brief. No extra libraries.

| Piece | Locked how | In easy words |
|---|---|---|
| Shop | **FastAPI** + uvicorn + CORS open | Keep the API we already named |
| Packages | **uv** + `pyproject.toml` + lockfile | One tool to install Python deps |
| Filing cabinet | **Postgres in Docker Compose**. App talks via `DATABASE_URL` | A box on the same machine as the files |
| Cable | **psycopg3** (`psycopg`), **sync** SQLModel `Session` | Wait for save+probe, then answer. No async DB yet |
| Table diary | **Alembic** from day 1. Do **not** rely on `create_all` in “real” runs. Tests may use a throwaway DB + migrations | Later phases add columns without breaking the old table |
| Measure file | **ffmpeg-python** `ffmpeg.probe()` (still needs **ffmpeg/ffprobe installed** on the machine — not inside the Postgres container) | Helper that calls ffprobe |
| Upload | **`UploadFile`**, read in **chunks**, count bytes, **413** if over 2 GB. Never `await file.read()` with no size | Sip the file so 2 GB does not fill RAM |
| Path JSON | Copy into `data/videos/{id}/`. No symlink | Same as product |
| Fetch file | **`FileResponse`** (Starlette Range is built in). `content_disposition_type="inline"` so a player can play, not force-download | Skip-to-time works later |
| Settings | pydantic-settings, `.env` gitignored | |
| Tests | pytest + httpx. Tiny mp4/audio fixtures. No GPU | |
| Size | Handful of files: `main.py`, `models.py`, `db.py`, `media/probe.py`, routes, `docker-compose.yml`, Alembic. ~200–300 lines each, split if bigger | |

**On the machine, not in pip:** ffmpeg (gives ffprobe). Docker for Postgres.

**Not this phase:** torch, Whisper, Gemma, React, S3, Modal, Redis, Celery, async SQL.

---

## Phase cards 2–13 (how to write the code)

### Phase 2 — Scissors

Laptop ffmpeg. `tools/frames.py`, `audio.py`, `caps.py`. Caps 64 photos / 30s. No HTTP extras.

### Phase 3 — Brain loop

Laptop owns the JSON loop. Gemma lives on **Modal vLLM (L4)**. Send **slices** (frames/audio already cut), not the file. Tests: FakeBrain, no GPU.

### Phase 4 — Speech

Laptop extracts audio slice/file for Whisper. Modal **ingest worker** (L4) runs faster-whisper turbo. Writes lines into laptop Postgres (API receives results). `transcript_status` updates as it goes.

### Phase 5 — Pictures

Laptop ffmpeg ~1 FPS. Modal ingest worker embeds with SigLIP. `visual_status` live. Delete bulk JPEGs after embed.

### Phase 6 — Sound

Same ingest worker, CLAP on 3s chunks. `audio_status` live. Counts in Python.

### Phase 7 — Export

Laptop ffmpeg. Local GET URL. No S3. No Modal.

### Phase 8 — Memory

Session fields on existing chat. No Redis. No Modal change.

### Phase 9 — UI shell

`web/` TanStack Start. Two routes. `lib/api.ts` talks to FastAPI. No extra UI kits.

### Phase 10 — Upload + live index panel

File picker on `/`. Byte % during POST. Then **open the video page while processing**. Spinner + four index lines (poll). Chat still off. No player yet.

### Phase 11 — Watch + ask

Video.js + chat. If still `processing`, keep the live index panel; chat disabled. After `ready`, chat on. Working… on send.

### Phase 12 — Clips + polish

Clip in chat. Phone stack. Delete. README. Same live panel if someone opens a video that is still indexing.

### Phase 13 — Slides

Same ingest worker after pictures. ColQwen2.x on unique frames. `slides_status` live. Gemma still reads the real frame.

---

**Point a coding agent here**

1. Read this file (how) + the matching `docs/phases/phase-XX.md` (what).
2. Implement **only** the phase you were told to do.
3. Stop. Do not start the next phase until we lock go-ahead for that slice.

Phase 1 code lives in `backend/`. Next code is Phase 2 only.
