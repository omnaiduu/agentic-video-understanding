# Phase 1 — Hold a video

**Status:** almost locked. Remaining questions are at the bottom.

Product (short): later you will ask questions about a long video. This phase does **not** do that. It only **takes a file, stores it, measures it, gives it an id**.

Related: [goal](../01-goal-and-context.md) · [stack](../08-frontend-backend.md) · [phase map](../12-build-phases.md)

---

## What this phase is (and is not)

Yes: **file intake**. An HTTP API that can receive a video or audio file, keep it on disk, remember it in a database, tell you duration and status.

No: website upload button, chat, ffmpeg cutting frames, Whisper, Gemma, clip export.

You prove it with curl or a test, not a browser app.

---

## Words

**SQLite** — a database that is one file on disk. We put a row per media file.

**SQLModel** — a small Python library (same author as FastAPI). You write a class:

```python
class Video(SQLModel, table=True):
    id: str
    duration_s: float | None
    status: str
```

That class **is** the table. SQLModel saves and loads rows. It sits on SQLAlchemy (the usual Python database tool) plus Pydantic (type checks). We are **not** training a model. The name is unfortunate. It just means “SQL + data model.”

Without it we would write SQL strings by hand. Fine for one table; messy when we add transcripts and chat.

**ffmpeg** — a program that can cut and convert video/audio.

**ffprobe** — the sibling that only **looks**. You point it at a file; it prints duration, whether there is video, whether there is audio, fps. It does not cut. Phase 1 uses ffprobe only. The machine needs ffmpeg installed (ffprobe comes with it).

---

## How it will work

Two ways in (locked: **both**):

1. **Upload** — `POST /videos` with the file bytes. This is what the website will use later.
2. **Path** — `POST /videos` with `{"path": "/home/you/talk.mp4"}`. For a file already on the server. We **copy** it into our folder (we own it; deleting your original later must not break us).

Then:

```
save to DATA_DIR/videos/{id}/original.{ext}
→ ffprobe
→ SQLite row
→ return JSON
```

Read back:

- `GET /videos` — list
- `GET /videos/{id}` — metadata JSON
- `GET /videos/{id}/file` — the actual bytes (so a future player can play it). **Proposed yes** — see questions.

**On disk**

```
data/app.db
data/videos/{uuid}/original.mp4    # or .mp3 / .wav / …
```

Keep the real extension. Do not rename audio to `.mp4`.

**Status**

| Value | Phase 1 meaning |
|---|---|
| `uploaded` | Landing, not probed yet |
| `processing` | Unused until later ingest. Keep the value. |
| `ready` | Saved + ffprobe OK |
| `error` | Unreadable file. Store `error_message`. |

POST waits until probe finishes (seconds). No job queue yet.

**Size:** default cap **2 GB**, set in config (`MAX_UPLOAD_BYTES`). Easy to raise. Unlimited is a good way to fill the disk; we will not do unlimited.

**Types (your direction):** **mp4 video** and **audio files**. Exact audio extensions still open (question below). ffprobe must succeed or we mark `error`.

**Row we store**

- id (UUID)
- original filename (so a library can show `talk.mp4`)
- path on disk
- kind: `video` or `audio` (from probe: has video stream or not)
- duration_s
- fps (null for audio-only)
- has_audio, has_video
- status, error_message
- created_at

Audio-only files are allowed. Later, picture tools simply will not apply. Whisper and sound search still will. We do **not** rename the API to `/media` unless you ask; `/videos` can hold audio rows.

**Path safety:** reject paths that are not a real file. Do not follow weird `../` tricks. Copy only.

---

## Plan (agent)

1. `backend/` Python 3.11+, `pyproject.toml`
2. FastAPI, CORS open, pydantic-settings
3. SQLModel + SQLite
4. Storage copy into `data/videos/{id}/original.{ext}`
5. ffprobe → fill the row
6. `POST /videos` (multipart **or** JSON path)
7. `GET /videos`, `GET /videos/{id}`
8. `GET /videos/{id}/file` if locked yes
9. Reject over 2 GB
10. Tests: tiny mp4, tiny wav/mp3, garbage → error, oversize → 413
11. `backend/README.md` — need **ffmpeg/ffprobe** installed

**Libraries:** fastapi, uvicorn, python-multipart, pydantic-settings, sqlmodel, pytest, httpx.

No torch, whisper, openai, React.

---

## Locked

- Both upload and path; **copy** on path
- FastAPI, `backend/` folder, UUID ids, no login, local disk
- Sync POST, no worker queue
- 2 GB default cap (config)
- SQLModel + SQLite (unless you veto after the explanation above)
- mp4 + audio (extensions: see open)
- Tests generate tiny files; no GPU

---

## Still open (answer to lock)

1. **Audio extensions?** Proposed: `.mp3`, `.wav`, `.m4a`, `.aac`, `.flac`, `.ogg`. Add/remove any.
2. **Give the file back?** `GET /videos/{id}/file` streams the saved file (needed later for the player). I would include it in Phase 1. OK?
3. **SQLModel** — any objection now that it is explained?
4. **Delete?** `DELETE /videos/{id}` removes row + folder. Useful, small. Include now or skip until the website needs it?

When these are answered, mark **LOCKED** and implement only this file.

## Done when

- Server starts
- Upload mp4 → ready + duration
- Register a path → same
- Upload audio → kind=audio, duration set, no fps required
- Garbage → error
- Over 2 GB → rejected
- GET metadata (and file, if we include it) works
- No chat, no UI, no frame cutting
