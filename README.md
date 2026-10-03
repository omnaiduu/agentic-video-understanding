# Agentic Video Understanding

Ask a question about a long video. The model searches an index, opens a short slice, then answers.

`backend/` is the API and the loop. `web/` is the library, player, and chat.

## How to run

You need Python 3.11+, [uv](https://docs.astral.sh/uv/), ffmpeg (which includes ffprobe), Docker, and Node.js. ffmpeg stays on the host. Postgres runs in Docker.

Three processes: Postgres, FastAPI, and the website.

### 1. Postgres

```bash
cd backend
docker compose up -d
```

Image `pgvector/pgvector:pg16`. Login `video` / `video` on `127.0.0.1:5432`, database `video`. Compose also creates `video_test` for pytest.

### 2. API

```bash
cd backend
cp .env.example .env
uv sync --group dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The example leaves `BRAIN=fake`. Chat then returns **503** until you set `BRAIN=vllm` and `VLLM_BASE_URL` to an OpenAI-compatible Gemma endpoint. Tests inject their own brain and do not need a GPU. Keep `.env` uncommitted.

Variables live in [backend/.env.example](backend/.env.example). The ones you usually edit:

| Variable | Role |
|---|---|
| `DATABASE_URL` | Postgres. Default `postgresql+psycopg://video:video@localhost:5432/video` |
| `DATA_DIR` | Original files and exports. Default `../data` from `backend/` |
| `BRAIN` | `fake` or `vllm` |
| `VLLM_BASE_URL` | Gemma endpoint when `BRAIN=vllm` |
| `VLLM_MODEL` | Default `google/gemma-4-E4B-it` |
| `UI_ORIGIN` | Where FastAPI loads the website from. Example value `http://127.0.0.1:3000` |

API routes: [backend/README.md](backend/README.md).

### 3. Website

```bash
cd web
cp .env.example .env
npm install
npm run dev
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000). `VITE_API_URL=/` in [web/.env.example](web/.env.example) keeps browser calls on that origin. Vite proxies `/videos` to FastAPI on port 8000. With `UI_ORIGIN` set, [http://127.0.0.1:8000](http://127.0.0.1:8000) serves the same pages.

Upload a file on `/`. You land on `/videos/:id`. Chat stays off until the file status is `ready`. The speech, picture, sound, and slide lines can still be building; look and listen work, and search may be incomplete.

Website notes: [web/README.md](web/README.md).

### Tests

```bash
cd backend && uv run pytest
cd web && npm test
```

## How it works

Gemma 4 E4B returns one JSON object. Python runs it. The actions are `look`, `listen`, `search`, `search_visual`, `search_audio`, `search_slides`, `export_clip`, `export_audio`, and `answer`. Photos and audio go back to the model as ordinary content. A second question on the same file reuses the indexes.

Four indexes, built once:

| Index | Model | Action |
|---|---|---|
| Speech | faster-whisper turbo, plus keyword search and E5 | `search` |
| Pictures | SigLIP 2 at about 1 frame per second | `search_visual` |
| Sounds | LAION-CLAP, 3 second chunks, 1.5 second hop | `search_audio` |
| Slides | ColQwen2 on unique frames | `search_slides` |

Retrieval finds a time. Gemma reads the frame or hears the slice and writes the answer. Counts of nearby sound hits are computed in Python.

Caps, enforced in `backend/app/tools/caps.py` and `backend/app/agent/schema.py`: **12** photos per look, **30** seconds of audio per listen, **12** JSON rounds, **60** seconds per export. A request over a cap is refused. Uploads stop at 2 GB.

Files live under `data/videos/{id}/` (gitignored). Postgres holds the rows and the vectors.

Optional Modal workers, off unless you point `.env` at them:

- `backend/modal_brain.py` — default E4B chat worker
- `backend/modal_brain_thinking.py` — E4B with thinking. Set `VLLM_THINKING_BASE_URL`. Leave `GEMMA_THINKING` false; the Watch page checkbox turns thinking on for one question.
- `backend/modal_brain_12b.py` — Gemma 4 12B. Set `VLLM_MODEL=google/gemma-4-12B-it` and `VLLM_BASE_URL` to that worker.
- `backend/modal_ingest.py` — speech, picture, sound, and slide embeddings

On the same eight questions, E4B scored 6 pass, 1 partial, and 1 fail. 12B scored 5 pass, 2 partial, and 1 fail. 12B listened, then cut the beep, and invented five claps. The default stayed E4B.

## Sources

- [Introducing Agentic Video in Gemini](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-agentic-video-in-gemini/) (1 Sep 2026)
- [Gemma 4 model card](https://ai.google.dev/gemma/docs/core/model_card_4)
- [SigLIP 2](https://arxiv.org/abs/2502.14786)
- [LAION CLAP](https://github.com/LAION-AI/CLAP)
- [ColQwen2](https://huggingface.co/vidore/colqwen2-v1.0)
