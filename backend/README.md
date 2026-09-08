# Backend (Phases 1–4)

Takes a video or audio file, stores it on disk, measures it with ffprobe, remembers it in Postgres. Python scissors cut a short slice. `POST /videos/{id}/chat` runs our look / listen / **search** / answer loop. Whisper writes a speech index once in the background; chat hybrid-searches those lines. No website, no SigLIP/CLAP.

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
# multipart upload
curl -F "file=@/path/to/clip.mp4" http://127.0.0.1:8000/videos

# or copy from a path on this machine
curl -H 'Content-Type: application/json' \
  -d '{"path":"/path/to/clip.mp4"}' \
  http://127.0.0.1:8000/videos
```

A ready file returns `status: "ready"` and `duration_s` after ffprobe. `transcript_status` starts as `processing` (or `skipped` if there is no audio). POST `/videos` does **not** wait for Whisper. Garbage that ffprobe cannot read is stored with `status: "error"`. Files larger than **2 GB** (`MAX_UPLOAD_BYTES`) are rejected with **413**.

Scissors are **Python functions**, not routes. Tests call them directly:

```bash
uv run pytest
```

Caps: at most **64** JPEGs per `get_frames`, **30 seconds** per `get_audio`. Oversize is an error (no silent shrink, no whole-file ffmpeg). Whisper ingest extracts the **whole** audio track with a separate helper (not `get_audio`).

## Chat

The laptop owns the loop. Gemma (on Modal vLLM, L4) only fills JSON. Tests inject a FakeBrain; default `BRAIN=fake` so pytest never calls a GPU.

```bash
# after a video is probe-ready (chat does not wait for Whisper)
curl -H 'Content-Type: application/json' \
  -d '{"message":"what did they say about pricing?"}' \
  http://127.0.0.1:8000/videos/VIDEO_ID/chat
```

JSON moves: `look`, `listen`, `search`, `answer`. `search` is our Python (`search_transcript`: Postgres FTS + pgvector + RRF, top 8 hits as text). Not vLLM `tools=`.

Real Gemma: deploy `modal_brain.py` (`modal deploy modal_brain.py`), set `BRAIN=vllm` and `VLLM_BASE_URL` to that server’s `/v1` URL.

Real Whisper: deploy `modal_ingest.py` (`modal deploy modal_ingest.py`), set `INGEST=modal`, `PUBLIC_BASE_URL` to a URL Modal can reach, and `INGEST_SECRET`. The worker POSTs lines back to `POST /internal/videos/{id}/transcript`. Default `INGEST=fake` writes an empty transcript so tests need no GPU.

## API

| Method | Path | What it does |
|---|---|---|
| POST | `/videos` | Multipart `file` **or** JSON `{"path": "..."}`. Copies into `data/videos/{id}/original.{ext}`, probes, returns the row. Spawns transcript ingest in the background. |
| GET | `/videos` | List |
| GET | `/videos/{id}` | Metadata, including `transcript_status` |
| GET | `/videos/{id}/file` | Stored bytes. `FileResponse` honors **Range** (for a later player). |
| POST | `/videos/{id}/chat` | `{ "message", "session_id"? }` → `{ answer, citations, steps, session_id }`. Our JSON loop, not native tools. |
| POST | `/internal/videos/{id}/transcript` | Modal (or tests) posts Whisper segments. Bearer `INGEST_SECRET`. |
| GET | `/internal/videos/{id}/audio` | Full wav for the ingest worker. Bearer `INGEST_SECRET`. |
| DELETE | `/videos/{id}` | Deletes the row, chat, transcript lines, **and** the folder |

No auth on the public video/chat routes. CORS is open.

Path JSON copies the file (no symlink). Paths that contain `..` are rejected.

## Layout

`data/videos/{id}/original.{ext}` lives at the **repo root** `data/` (gitignored). Postgres URL is `DATABASE_URL`. Migrations are Alembic; do not use `create_all` for real runs. Optional `uv sync --extra local-ingest` if you want faster-whisper / E5 on the laptop instead of Modal.
