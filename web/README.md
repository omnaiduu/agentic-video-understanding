# Website (Phases 9–11)

TanStack Start app for the library, upload, live indexes, **player**, and **chat**. FastAPI is still the only API. This folder does not run ffmpeg, Whisper, SigLIP, CLAP, or Gemma. The browser talks to FastAPI with `VITE_API_URL` (see `.env.example`). No Start server function is a second backend.

Pick a file on `/`. After upload you land on `/videos/$id`. Video.js plays `GET {API}/videos/{id}/file`. Ask a question; the site POSTs chat, keeps `session_id` in localStorage for that video, and turns citations into seek chips. Tool steps sit in a collapsed Details block. Clip download UI is still off (Phase 12).

If indexes are still building, the four live lines stay and chat stays off.

## Run with FastAPI

Terminal 1 — API:

```bash
cd backend
cp .env.example .env
docker compose up -d
uv sync --group dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Chat needs a real brain (`BRAIN=vllm` + `VLLM_BASE_URL`) or a test FakeBrain. `BRAIN=fake` with no script returns 503.

Terminal 2 — website:

```bash
cd web
cp .env.example .env
npm install
npm run dev
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000).

## Check

```bash
npm test
```

Tests mock `fetch` / XHR / Video.js. They do not start Gemma.

## Routes

| Path | What it does |
|---|---|
| `/` | File picker + `GET {API}/videos` |
| `/videos/$videoId` | Player, live indexes, `POST {API}/videos/:id/chat` |
