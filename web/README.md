# Website (Phases 9–10)

TanStack Start app for the library and the watch+ask **shell**. FastAPI is still the only API. This folder does not run ffmpeg, Whisper, SigLIP, CLAP, or Gemma. The browser talks to FastAPI with `VITE_API_URL` (see `.env.example`). No Start server function is a second backend.

Pick a file on `/`. The browser POSTs multipart to FastAPI and shows **byte %**. When the POST returns, the site opens `/videos/$id` even if indexes are still building. That page polls `GET /videos/:id` and shows four live lines (speech, pictures, sounds, slides). Chat and the player are still off.

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

Terminal 2 — website:

```bash
cd web
cp .env.example .env
npm install
npm run dev
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000). Choose an mp4 or audio file (2 GB cap, same as the API). Oversize returns **413** and the page shows an error. If FastAPI is down, the page shows an error instead of crashing.

## Check

```bash
npm test
```

Tests mock `fetch` / XHR. They do not start Gemma. They do not ship a 2 GB fixture.

## Routes

| Path | What it does |
|---|---|
| `/` | File picker + `GET {API}/videos` |
| `/videos/$videoId` | `GET {API}/videos/:id` (poll while indexes run) |

shadcn this phase: Button, Card, Badge, Progress.
