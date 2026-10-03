# Backend

FastAPI stores a video or audio file, measures it with ffprobe, and keeps the row in Postgres. Python cuts a short slice. `POST /videos/{id}/chat` runs look, listen, search, search_visual, search_audio, search_slides, export_clip, export_audio, and answer. Whisper, SigLIP, CLAP, and ColQwen each write an index once. Export re-encodes a clip of at most 60 seconds and returns a GET URL. A follow-up reuses the same `session_id`. The website is in `web/`.

## What you need

- Python 3.11+ and [uv](https://docs.astral.sh/uv/)
- ffmpeg, which provides ffprobe. It is not installed by pip, and it is not inside the Postgres container.
- Docker, for Postgres with pgvector (`docker compose` in this folder)

Full three-process runbook: [../README.md](../README.md).

## Run

```bash
cd backend
cp .env.example .env
docker compose up -d
uv sync --group dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Compose uses `pgvector/pgvector:pg16` and creates `video_test` for pytest.

```bash
curl -F "file=@/path/to/clip.mp4" http://127.0.0.1:8000/videos
uv run pytest
```

`POST /videos` returns after ffprobe. Speech, picture, sound, and slide indexes continue in the background. Their status fields start as `processing`, or `skipped` when that channel does not apply.

Caps: at most **12** JPEGs per `get_frames`, **30** seconds per `get_audio`, **12** JSON rounds, **60** seconds per `export_clip` or `export_audio`. A request over a cap is refused. Picture ingest is a separate extract at about 1 frame per second. Sound ingest is 3 second chunks with a 1.5 second hop. Slide ingest keeps unique pages from that frame stream, then ColQwen embeds those pages. Bulk JPEGs and chunk wavs are deleted after embed. Export files stay until the video is deleted.

## Chat

This process owns the loop. Gemma, on a Modal vLLM worker, only fills JSON. Tests inject a fake brain. The example env sets `BRAIN=fake`, and chat returns 503 until `BRAIN=vllm` and `VLLM_BASE_URL` are set.

The default worker is E4B (`modal_brain.py`, app `agentic-video-brain`). Thinking is a second E4B app (`modal_brain_thinking.py`, `agentic-video-brain-e4b-thinking`) with `--reasoning-parser gemma4`. Leave that flag off the default worker. The 12B worker (`modal_brain_12b.py`, `agentic-video-brain-12b`) serves `google/gemma-4-12B-it` from Google's QAT W4A16 checkpoint so it fits an L4. Point `VLLM_BASE_URL` and `VLLM_MODEL` at it in `.env` when you want it. Set `VLLM_THINKING_BASE_URL` for the thinking worker. Deploying 12B does not replace the E4B app.

JSON moves: `look`, `listen`, `search`, `search_visual`, `search_audio`, `search_slides`, `export_clip`, `export_audio`, `answer`. `search_slides` compares ColQwen query tokens to unique-slide patches and returns up to 8 times. Scores are a map. Gemma looks at a hit and reads the frame. Export re-encodes on this machine and returns `/videos/{id}/exports/{export_id}`. Gemma receives that URL as text. Follow-ups send the same `session_id`. The last 3 time windows go into the prompt as text.

Real ingest uses `modal_ingest.py` (a different Modal app from chat). This machine writes the media; Modal embeds it and posts back. Defaults `INGEST=fake`, `EMBEDDER=fake`, `VISUAL_EMBEDDER=fake`, `AUDIO_EMBEDDER=fake`, and `SLIDE_EMBEDDER=fake` so tests need no GPU. `uv sync --extra local-ingest` installs Whisper, E5, SigLIP, CLAP, and ColQwen on this machine instead.

## API

| Method | Path | What it does |
|---|---|---|
| POST | `/videos` | Multipart `file` or JSON `{"path": "..."}`. Probes, returns the row, starts ingest in the background. |
| GET | `/videos` | List |
| GET | `/videos/{id}` | Metadata, including `transcript_status`, `visual_status`, `audio_status`, and `slides_status` |
| GET | `/videos/{id}/file` | Stored bytes. Range requests work. |
| POST | `/videos/{id}/chat` | `{ "message", "session_id"?, "thinking"? }` → `{ answer, citations, steps, session_id, export_url?, thinking, thoughts }`. Omit `session_id` for a new thread. `thinking: true` needs `VLLM_THINKING_BASE_URL`. |
| POST | `/videos/{id}/chat/stream` | Same body as `/chat`. Newline-delimited JSON: pings, then `event: done` or `event: error`. The website uses this. |
| GET | `/videos/{id}/chat/{session_id}/result` | Query `message`. Returns the saved turn, or `{ "status": "pending" }`. |
| GET | `/videos/{id}/exports/{export_id}` | Exported mp4 or wav. Range requests work. |
| DELETE | `/videos/{id}` | Deletes the row, chat, indexes, exports, and the folder |

Ingest workers call `/internal/videos/{id}/...` with bearer `INGEST_SECRET`. Public video and chat routes have no auth. CORS is open.

Original files live at the repo-root `data/videos/{id}/` directory (gitignored).
