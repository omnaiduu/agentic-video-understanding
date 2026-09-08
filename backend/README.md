# Phase 1 — Hold a video

Takes a video or audio file, stores it on disk, measures it with ffprobe, remembers it in Postgres. No chat, no website, no frame cutting.

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

```bash
uv run pytest
```

## API

| Method | Path | What it does |
|---|---|---|
| POST | `/videos` | Multipart `file` **or** JSON `{"path": "..."}`. Copies into `data/videos/{id}/original.{ext}`, probes, returns the row. |
| GET | `/videos` | List |
| GET | `/videos/{id}` | Metadata |
| GET | `/videos/{id}/file` | Stored bytes. `FileResponse` honors **Range** (for a later player). |
| DELETE | `/videos/{id}` | Deletes the row **and** the folder |

No auth. CORS is open.

Path JSON copies the file (no symlink). Paths that contain `..` are rejected.

## Layout

`data/videos/{id}/original.{ext}` lives at the **repo root** `data/` (gitignored). Postgres URL is `DATABASE_URL`. Migrations are Alembic; do not use `create_all` for real runs.
