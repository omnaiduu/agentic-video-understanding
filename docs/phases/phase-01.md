# Phase 1 — Hold a video

**Status: LOCKED.** An agent may implement **only** this file. Do not start Phase 2 from here.

Product (short): later you will ask questions about a long video. This phase does **not** do that. It only **takes a file, stores it, measures it, gives it an id**.

Related: [goal](../01-goal-and-context.md) · [stack](../08-frontend-backend.md) · [phase map](../12-build-phases.md) · next: [Phase 2](phase-02.md)

---

## What this phase is

**File intake.** An HTTP API that receives a video or audio file, keeps it on disk, remembers it in Postgres, tells you duration and status.

Not: website, chat, frame cutting, Whisper, Gemma, clip export.

---

## Words

**SQLite** — old default (one file). **Corrected:** we use **PostgreSQL** (your pick). Same SQLModel classes; `DATABASE_URL` is Postgres. Files still live on disk.

**SQLModel** — Python library (not an AI model). A class becomes a database table. Save/load rows.

**ffprobe** — comes with ffmpeg. Inspects a file (duration, video?, audio?). Does not cut. Phase 1 uses this only. ffmpeg must be installed.

---

## Locked decisions

| Topic | Decision |
|---|---|
| How files enter | **Upload** (multipart) **and** **path** (JSON). Path **copies** into our folder. |
| Types | **mp4** video, plus **any audio** ffprobe accepts (mp3, wav, m4a, aac, flac, ogg, …). Probe must succeed. |
| Size | **2 GB** default (`MAX_UPLOAD_BYTES`). Configurable. Not unlimited. |
| Database | **PostgreSQL** + SQLModel (**corrected**; was SQLite) |
| Ids | UUID. Folder `data/videos/{id}/original.{ext}` (keep real extension). |
| Auth | None |
| POST | Sync: return after save + ffprobe. No job queue. |
| Fetch bytes | **`GET /videos/{id}/file`** — stream the stored file (Range so a later player can seek). We include this because the website player will need it; metadata JSON is not playable. |
| Delete | **`DELETE /videos/{id}`** — delete the **row and the whole folder** (original file too). |
| Auto-clean when a chat ends | **Not this phase** (there is no chat yet). Intent: a one-off demo should not keep files forever. Design that when sessions exist (later). Mechanism we already have: DELETE. |

**Row**

- id, original filename, path
- kind: `video` or `audio` (from probe)
- duration_s, fps (null if audio-only), has_audio, has_video
- status, error_message, created_at

**Status:** `uploaded` → `ready` or `error`. Keep `processing` unused until ingest.

**Path safety:** real file only; no `../` tricks; copy, do not link.

**API name:** keep `/videos` even if some rows are audio.

---

## How it works

```
POST /videos          upload file OR {"path": "..."}
  → copy to data/videos/{id}/original.{ext}
  → ffprobe → Postgres → JSON

GET /videos
GET /videos/{id}      metadata
GET /videos/{id}/file bytes
DELETE /videos/{id}   row + folder
```

---

## Plan (agent)

1. `backend/` Python 3.11+, `pyproject.toml`
2. FastAPI, CORS open, pydantic-settings
3. SQLModel + **PostgreSQL** (`DATABASE_URL`)
4. Routes above
5. Reject over 2 GB (413)
6. Tests: tiny mp4, tiny audio, garbage → error, oversize, delete removes files
7. `backend/README.md` — ffmpeg/ffprobe required
8. gitignore `data/`, `.env`

**Libraries:** fastapi, uvicorn, python-multipart, pydantic-settings, sqlmodel, pytest, httpx.

No torch, whisper, openai, React. No `web/` folder.

---

## Done when

- Upload mp4 → `ready` + duration
- Path register → same
- Audio → `kind=audio`
- Garbage → `error`
- Over 2 GB → rejected
- GET file returns bytes
- DELETE removes row and files
- No chat, no UI, no frame cutting
