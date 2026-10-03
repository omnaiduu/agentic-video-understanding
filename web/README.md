# Website

TanStack Start app for the library, upload, the four index lines, the player, chat, clips in the thread, a stacked phone layout, and delete. FastAPI is the only API. This folder does not run ffmpeg, Whisper, SigLIP, CLAP, ColQwen, or Gemma. The browser calls FastAPI through `VITE_API_URL` (see `.env.example`).

Pick a file on `/`. After upload you land on `/videos/$id`. Video.js plays `GET {API}/videos/{id}/file`. The site posts chat, keeps `session_id` in localStorage for that video, and turns citations into seek chips. When the answer includes `export_url`, a mini player and **Download** render inside that turn. Tool steps sit in a collapsed details block. On a narrow screen the player stacks above chat. **Delete** confirms, then calls `DELETE /videos/{id}`.

Chat stays off until the file status is `ready`. If indexes are still building, the four lines stay on screen and a note says look and listen work while search may be incomplete.

## Run with FastAPI

Root runbook: [../README.md](../README.md).

Terminal 1 — API:

```bash
cd backend
cp .env.example .env
docker compose up -d
uv sync --group dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Chat needs `BRAIN=vllm` and `VLLM_BASE_URL`, or a test fake brain. `BRAIN=fake` with no script returns 503.

Terminal 2 — website:

```bash
cd web
cp .env.example .env
npm install
npm run dev
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000). The example `VITE_API_URL=/` keeps calls on that origin. Vite proxies `/videos` to port 8000.

## Check

```bash
npm test
```

Tests mock `fetch`, XHR, and Video.js. They do not start Gemma.

## Routes

| Path | What it does |
|---|---|
| `/` | File picker and `GET {API}/videos` |
| `/videos/$videoId` | Player, index lines, chat, in-thread clips, delete |
