# Phase 1 — Hold a video

**Status:** not locked. Human answers the questions at the bottom first. Then an agent implements **only** this file.

Product background (short): the finished app lets you upload a long video and ask questions. A model jumps to short moments instead of watching the whole file. Speech / picture / sound indexes, the chat loop, clip export, and the website all come **after** this phase. They all need the same thing first: **a video on disk with an id**.

This phase builds that. It is not a mini product.

Related: [goal](../01-goal-and-context.md) · [stack](../08-frontend-backend.md) · [phase map](../12-build-phases.md)

---

## What we are trying to do

Give the app a **shelf**.

You add a video. The app:

1. Keeps the file in a known folder
2. Gives it a stable id
3. Measures it (how long, fps, has sound)
4. Remembers that in a database
5. Lets you read it back over HTTP

That is the whole phase.

Later, ffmpeg will cut frames from **this** file. Whisper will transcribe **this** file. The website will list **these** rows. If we skip this and jump to models, those pieces have nowhere to hang.

## What you can do when Phase 1 is done

Start the API. Add a video. Fetch it. See duration. That is success.

You cannot ask questions yet. You cannot cut a clip. There is no website. That is correct.

## What we will not build here

- Cutting frames or audio (`get_frames` / `get_audio`)
- Gemma / any LLM
- Whisper, SigLIP, CLAP
- Chat, export, login
- The React app

We **will** run **ffprobe** (inspect only). We will **not** run ffmpeg as a cutter.

---

## Why these tools (not “because a doc said so”)

**Python.** Whisper, SigLIP, CLAP, and the Gemma client are Python. The API should be Python so we do not glue two languages for the ML path.

**FastAPI + uvicorn.** HTTP API in Python. The future website talks to this. Async is useful later when ingest is slow; we do not need a job queue yet.

**SQLite.** A database that is one file. No extra server. Enough for videos, then transcripts, then chat. Postgres is for many users — not now.

**SQLModel.** We describe a `Video` class; it becomes a table. Raw `sqlite3` is fine for one table and painful for five. We will have more tables.

**ffprobe.** Ships with ffmpeg. Reads duration/fps/audio **without** decoding the whole movie. We store duration so a later agent can be told “this is 2 hours; do not load it.”

**UUID id.** Folder name `data/videos/{id}/original.mp4`. Not `1.mp4`, `2.mp4`. Later indexes and exports live under the same `{id}/`.

**No auth.** One machine. Login is a different product slice.

**CORS allow-all in dev.** So Phase 9’s website on another port can call this API. Tighten only if we ever put a real domain in front.

**Tests generate a tiny mp4 with ffmpeg.** No 2-hour file in git. No GPU.

---

## How it works

```
you → POST /videos → save bytes to disk → ffprobe → SQLite row → status ready
you → GET /videos/{id} → json (id, duration, fps, has_audio, status)
you → GET /videos → list
```

**On disk**

```
DATA_DIR/app.db
DATA_DIR/videos/{id}/original.mp4
```

Later phases add `indexes/`, `exports/` next to `original.mp4`. Do not create those folders yet.

**Status values (put them on the row now, even if unused)**

| Status | Meaning in Phase 1 |
|---|---|
| `uploaded` | File is landing / not probed yet |
| `processing` | Unused until Whisper/etc. Keep the value so we do not migrate. |
| `ready` | File is saved and ffprobe succeeded. (Later, `ready` will also mean indexes exist. For now it only means *shelf is filled*.) |
| `error` | Not a readable video, or probe failed. Keep `error_message`. |

**POST is synchronous.** The request returns after save + ffprobe. ffprobe is seconds, not minutes. Whisper (later) is minutes — that ingest will go background. Do not build a worker queue here.

**Cap how big a file can be** so a bad upload cannot fill the disk. Default proposed: **2 GB**. Open question below.

---

## Plan (what an agent implements)

1. `backend/` with `pyproject.toml` (Python 3.11+).
2. FastAPI app: config, DB init, CORS.
3. `Video` table as above.
4. Storage helper: write `original.mp4`.
5. `media.py`: run ffprobe, parse duration / fps / has_audio.
6. Routes: `POST /videos`, `GET /videos`, `GET /videos/{id}`.
7. `.gitignore`: `data/`, `.env`, `__pycache__/`.
8. pytest: happy path, bad file → `error`, list endpoint.
9. `backend/README.md`: how to run.

**Layout**

```
backend/
  pyproject.toml
  README.md
  app/
    main.py
    config.py
    db.py
    models.py
    storage.py
    media.py
    routers/videos.py
  tests/
    test_videos.py
```

No `web/` folder yet.

**Libraries to add**

- fastapi, uvicorn, python-multipart
- pydantic-settings
- sqlmodel
- pytest, httpx

Nothing else (no torch, no whisper, no openai).

**Config**

- `DATA_DIR` (default `./data`)
- `DATABASE_URL` (default SQLite under `DATA_DIR`)
- `MAX_UPLOAD_BYTES` (from the size question)

---

## Open options (human)

### 1. How does a video enter the app?

The finished website will **upload** a file. So the API must support upload **sometime**. Phase 1 can do it now, or only accept a path and add upload later. Upload now means the production path exists on day one; tests just POST a tiny mp4.

A **disk path** (`{"path": "/home/you/talk.mp4"}`) copies or references a file already on the machine. Nice for a 2-hour local file. Useless for a browser (the browser does not have your server paths).

| Choice | What it means |
|---|---|
| Upload only | `POST` multipart file. Website-ready. Tests upload. |
| Path only | Faster for local big files. Website cannot use this. We would add upload in the UI phase. |
| Both | Upload is the product. Path is a helper for local/dev. A bit more code. |

**Recommendation: both.** One extra branch in `POST /videos`. If you want the smallest Phase 1, pick **upload only** — the website needs it anyway.

If “both”: path can **copy** into `data/videos/{id}/` (simple, always owned by us) or **link** to the original (saves disk, original might get deleted). **Recommendation: copy.** We own the file.

### 2. How big can a video be?

Pick a cap. 2 GB is a reasonable talk/lecture. 4 GB if you care about long 1080p. “No cap” will fill the disk.

**Recommendation: 2 GB.**

### 3. Which file types?

| Choice | What it means |
|---|---|
| `.mp4` only | Simple. Enough for v1 of the complete app. |
| Anything ffprobe can read (mp4, mkv, webm, mov, …) | More flexible. Probe fails on garbage either way. |

**Recommendation: accept common video types; ffprobe decides if it is real.** Reject if probe fails. Do not write a giant codec list.

### 4. SQLModel — any objection?

Default is SQLite + SQLModel. If you hate that, say so. Otherwise we use it.

---

## Already decided (do not re-ask)

- FastAPI, Python 3.11+
- Folder name `backend/` (website later: `web/`)
- UUID ids
- No login
- Local disk (cloud bucket later, same `storage.py` idea)
- Sync POST (no job queue)
- CORS open in dev
- Tests synthesize a tiny mp4

---

## Done when

- `uvicorn` starts
- Add a video → GET returns `status=ready` and `duration_s > 0`
- Garbage file → `status=error`
- Oversize file → rejected
- Tests pass with no GPU and no extra models
- No chat, no UI, no frame extraction

---

## Questions for the human (answer these to lock)

1. **Enter a video:** upload only, path only, or both? (Recommend both; if both, we copy the file.)
2. **Max size:** 2 GB OK, or another number?
3. **Types:** mp4 only, or any container ffprobe understands?
4. **SQLModel:** OK?

After answers, mark this phase **LOCKED** and implement only this file.
