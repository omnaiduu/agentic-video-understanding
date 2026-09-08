# Backend (Phases 1–3)

Takes a video or audio file, stores it on disk, measures it with ffprobe, remembers it in Postgres. Python scissors cut a short slice. `POST /videos/{id}/chat` runs our look / listen / answer loop. No website, no search, no Whisper.

## What you need on the machine

- **Python 3.11+** and [uv](https://docs.astral.sh/uv/)
- **ffmpeg** (this gives **ffprobe**). Not installed by pip. Not inside the Postgres container.
- **Docker** for Postgres (`docker compose` in this folder)

## Run

```bash
cd backend
cp .env.example .env          # edit if your Postgres is not local
docker compose up -d
uv sync --group dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Compose also creates a `video_test` database for pytest. ffmpeg and ffprobe stay on the **host**, not in the Postgres image.

Check:

```bash
# multipart upload
curl -F "file=@/path/to/clip.mp4" http://127.0.0.1:8000/videos

# or copy from a path on this machine
curl -H 'Content-Type: application/json' \
  -d '{"path":"/path/to/clip.mp4"}' \
  http://127.0.0.1:8000/videos
```

A ready file returns `status: "ready"` and `duration_s`. Garbage that ffprobe cannot read is stored with `status: "error"`. Files larger than **2 GB** (`MAX_UPLOAD_BYTES`) are rejected with **413**.

Scissors are **Python functions**, not routes. Tests call them directly:

```bash
uv run pytest
```

Caps: at most **64** JPEGs per `get_frames`, **30 seconds** per `get_audio`. Oversize is an error (no silent shrink, no whole-file ffmpeg).

## Chat

The laptop owns the loop. Gemma (on Modal vLLM, L4) only fills JSON. Tests inject a FakeBrain; default `BRAIN=fake` so pytest never calls a GPU.

```bash
# after a video is ready
curl -H 'Content-Type: application/json' \
  -d '{"message":"what happens at 0:10?"}' \
  http://127.0.0.1:8000/videos/VIDEO_ID/chat
```

Real Gemma: deploy `modal_brain.py` (`modal deploy modal_brain.py`), set `BRAIN=vllm` and `VLLM_BASE_URL` to that server’s `/v1` URL. The client uses `response_format` JSON schema and never sends `tools=`. Cuts are attached as user image/audio parts.

## API

| Method | Path | What it does |
|---|---|---|
| POST | `/videos` | Multipart `file` **or** JSON `{"path": "..."}`. Copies into `data/videos/{id}/original.{ext}`, probes, returns the row. |
| GET | `/videos` | List |
| GET | `/videos/{id}` | Metadata |
| GET | `/videos/{id}/file` | Stored bytes. `FileResponse` honors **Range** (for a later player). |
| POST | `/videos/{id}/chat` | `{ "message", "session_id"? }` → `{ answer, citations, steps, session_id }`. Our JSON loop, not native tools. |
| DELETE | `/videos/{id}` | Deletes the row, chat sessions, **and** the folder |

No auth. CORS is open.

Path JSON copies the file (no symlink). Paths that contain `..` are rejected.

## Layout

`data/videos/{id}/original.{ext}` lives at the **repo root** `data/` (gitignored). Postgres URL is `DATABASE_URL`. Migrations are Alembic; do not use `create_all` for real runs.
