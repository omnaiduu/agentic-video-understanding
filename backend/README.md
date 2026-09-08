# Backend (Phases 1–8)

Takes a video or audio file, stores it on disk, measures it with ffprobe, remembers it in Postgres. Python scissors cut a short slice. `POST /videos/{id}/chat` runs our look / listen / search / search_visual / search_audio / export_clip / export_audio / answer loop. Whisper writes a speech index once; SigLIP writes a picture index once; CLAP writes a sound index once. Export re-encodes a ≤60s mp4 or wav onto disk and returns a GET URL. A follow-up reuses the same `session_id` and the last 3 time windows as **text**. The website lives in `web/` (Phase 9) and only GETs this API.

## What you need on the machine

- **Python 3.11+** and [uv](https://docs.astral.sh/uv/)
- **ffmpeg** (this gives **ffprobe**). Not installed by pip. Not inside the Postgres container.
- **Docker** for Postgres with **pgvector** (`docker compose` in this folder)

## Run

```bash
cd backend
cp .env.example .env          # edit if your Postgres is not local
docker compose up -d
uv sync --group dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Compose uses `pgvector/pgvector:pg16` and also creates a `video_test` database for pytest. ffmpeg and ffprobe stay on the **host**.

Check:

```bash
curl -F "file=@/path/to/clip.mp4" http://127.0.0.1:8000/videos
```

A ready file returns `status: "ready"` after ffprobe. `transcript_status`, `visual_status`, and `audio_status` start as `processing` (or `skipped` if that channel does not apply). POST `/videos` does **not** wait for Whisper, SigLIP, or CLAP.

```bash
uv run pytest
```

Caps: at most **64** JPEGs per `get_frames`, **30 seconds** per `get_audio`, **60 seconds** per `export_clip` / `export_audio`. Oversize is refused (not shrunk). Picture **ingest** is a separate ~1 FPS extract (not the look cap). Sound **ingest** is 3s chunks with a 1.5s hop (not the listen cap). Bulk JPEGs and chunk wavs are deleted after embed. Export files are **kept** until the video is deleted.

## Chat

The laptop owns the loop. Gemma (on Modal vLLM, L4) only fills JSON. Tests inject a FakeBrain; default `BRAIN=fake`.

JSON moves: `look`, `listen`, `search`, `search_visual`, `search_audio`, `export_clip`, `export_audio`, `answer`. `search_audio` is our Python (CLAP text tower → pgvector KNN, top 8 windows, then merge nearby hits and `len()`). Export re-encodes on the laptop (not stream-copy) and returns `/videos/{id}/exports/{export_id}`. Gemma gets that URL as text, never the clip bytes. Follow-ups send the same `session_id`; last 3 look/listen/search/export windows go into the prompt as text (not old JPEGs/wavs). Not vLLM `tools=`.

Real sound ingest: same `modal_ingest.py` app, function `embed_audio` (not the chat GPU). Laptop ffmpeg writes 3s chunks; Modal embeds; POST `/internal/videos/{id}/sound`. Default `INGEST=fake` and `AUDIO_EMBEDDER=fake` so tests need no GPU.

## API

| Method | Path | What it does |
|---|---|---|
| POST | `/videos` | Multipart `file` **or** JSON `{"path": "..."}`. Probes, returns the row. Spawns speech + picture + sound ingest in the background. |
| GET | `/videos` | List |
| GET | `/videos/{id}` | Metadata, including `transcript_status`, `visual_status`, and `audio_status` |
| GET | `/videos/{id}/file` | Stored bytes. Range-friendly. |
| POST | `/videos/{id}/chat` | `{ "message", "session_id"? }` → `{ answer, citations, steps, session_id, export_url? }`. Omit `session_id` for a new thread. |
| GET | `/videos/{id}/exports/{export_id}` | Exported mp4 or wav. Range-friendly. |
| POST | `/internal/videos/{id}/transcript` | Whisper segments. Bearer `INGEST_SECRET`. |
| GET | `/internal/videos/{id}/audio` | Full wav for the ingest worker. |
| POST | `/internal/videos/{id}/visual` | SigLIP frames `{t_s, embedding}`. Bearer `INGEST_SECRET`. |
| GET | `/internal/videos/{id}/frames` | Tar of 1 FPS JPEGs for the ingest worker. |
| POST | `/internal/videos/{id}/sound` | CLAP chunks `{start_s, end_s, embedding}`. Bearer `INGEST_SECRET`. |
| GET | `/internal/videos/{id}/chunks` | Tar of 3s wav slices for the ingest worker. |
| DELETE | `/videos/{id}` | Deletes the row, chat, transcript, visual frames, audio chunks, exports, **and** the folder |

No auth on the public video/chat routes. CORS is open.

## Layout

`data/videos/{id}/original.{ext}` lives at the **repo root** `data/` (gitignored). Optional `uv sync --extra local-ingest` if you want Whisper / E5 / SigLIP / CLAP on the laptop instead of Modal.
