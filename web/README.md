# Website (Phase 9 — UI shell)

TanStack Start app for the library and the watch+ask **shell**. FastAPI is still the only API. This folder does not run ffmpeg, Whisper, SigLIP, CLAP, or Gemma. The browser talks to FastAPI with `VITE_API_URL` (see `.env.example`). No Start server function is a second backend.

This phase has **no upload form, no player, and no chat**. Curl a file into FastAPI, then open `/`.

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

Open [http://127.0.0.1:3000](http://127.0.0.1:3000). Empty library is expected until you upload:

```bash
curl -F "file=@/path/to/clip.mp4" http://127.0.0.1:8000/videos
```

Then refresh. Click a row for `/videos/$videoId` (title, duration, status, Phase 11 placeholders). If FastAPI is down, the page shows an error instead of crashing.

## Check

```bash
npm test
```

Tests mock `fetch`. They do not start Gemma.

## Routes

| Path | Query |
|---|---|
| `/` | `GET {API}/videos` |
| `/videos/$videoId` | `GET {API}/videos/:id` |

shadcn this phase: Button, Card, Badge only.
