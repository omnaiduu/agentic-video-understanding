# Agentic Video Understanding

Ask a question about a long video. The model does not watch every second. It holds a remote: search a phone book, open a short slice, then answer.

This is an open-weight copy of **Google Gemini’s agentic video understanding** (1 Sep 2026). Google did not ship a new video model. They shipped a tool loop. This repo ships the same idea with weights we can host.

**`main` is the app.** `backend/` is the API and the loop. `web/` is the library, player, and chat. `docs/` is why it is built this way, including the 13 phases and the live tests.

**Goal:** talks, slides, sports, CCTV, sounds. Find the moment, look or listen to a short slice, answer with a timestamp, optionally export a clip that plays in the chat. A second question on the same file does not rebuild the indexes.

---

## One-sentence product

**Gemma 4 E4B (fills a JSON form) + our Python loop + ffmpeg (scissors) + four phone books built once: Whisper (speech), SigLIP 2 (pictures), CLAP (sounds), ColQwen2.x (slides) + a TanStack Start website.**

ColQwen2.x and `search_slides` are for questions like “which slide had **Pro $99**?” when nobody said the number. Gemma still reads the real frame; ColQwen only finds the time.

| Piece | Where |
|---|---|
| FastAPI, scissors, indexes, JSON loop | `backend/` |
| Gemma on Modal (E4B default, optional thinking worker, optional 12B) | `backend/modal_brain.py` and the sibling workers |
| Ingest on a separate Modal app | `backend/modal_ingest.py` |
| Library, upload, Video.js, chat, clips | `web/` |
| Decisions, phases, live tests | `docs/` |

Tests do not need a GPU. Chat tests inject a fake brain. Real answers need `BRAIN=vllm` and a Modal URL in `.env` (gitignored). Copy `backend/.env.example`. Do not commit secrets.

---

## How to run (Postgres + FastAPI + website)

You need **three processes**: Postgres (Docker), FastAPI, and the TanStack Start app. ffmpeg / ffprobe stay on the **host**, not in the Postgres container. The browser talks only to FastAPI (`VITE_API_URL`). It never talks to Gemma.

### 1. Postgres with pgvector

```bash
cd backend
docker compose up -d
```

Compose image: `pgvector/pgvector:pg16`. Default login is `video` / `video` on `127.0.0.1:5432`, database `video`. It also creates `video_test` for pytest.

### 2. FastAPI

```bash
cd backend
cp .env.example .env
uv sync --group dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Useful env vars in `backend/.env`:

| Variable | What it does |
|---|---|
| `DATABASE_URL` | Postgres URL (default `postgresql+psycopg://video:video@localhost:5432/video`) |
| `DATA_DIR` | Where original files and exports live (`../data` from `backend/`) |
| `MAX_UPLOAD_BYTES` | Upload cap (2 GB) |
| `BRAIN` | `fake` (tests / 503 unless injected) or `vllm` |
| `VLLM_BASE_URL` | OpenAI-compatible Gemma endpoint when `BRAIN=vllm` |
| `VLLM_API_KEY` | Optional; default `EMPTY` |
| `VLLM_MODEL` | Default `google/gemma-4-E4B-it`. For the 12B A/B only: `google/gemma-4-12B-it` against `modal_brain_12b.py` (do not commit) |
| `GEMMA_THINKING` | Default `false`. Server-side default for Watch thinking; the checkbox still overrides |
| `VLLM_THINKING_BASE_URL` | E4B thinking worker (`modal_brain_thinking.py`). Empty → `thinking: true` returns 503 |
| `INGEST` / `EMBEDDER` / `VISUAL_EMBEDDER` / `AUDIO_EMBEDDER` / `SLIDE_EMBEDDER` | `fake` unless you wire Modal or local models |

Chat needs a real brain (`BRAIN=vllm` + `VLLM_BASE_URL`) or a test FakeBrain. `BRAIN=fake` with no script returns **503**.

More API detail: [backend/README.md](backend/README.md).

### 3. Website

```bash
cd web
cp .env.example .env
npm install
npm run dev
```

`web/.env`:

| Variable | What it does |
|---|---|
| `VITE_API_URL` | FastAPI origin the **browser** calls. Default `http://127.0.0.1:8000` |

Open [http://127.0.0.1:3000](http://127.0.0.1:3000). Pick a file on `/`. After upload you land on `/videos/:id`. Chat stays off until Speech / Picture / Sound / Slide lines finish. Ask a question; citations seek the source player. If the answer includes an `export_url`, a mini player and **Download** appear **in that chat turn**. On a phone (~768px) the source player stacks above chat. **Delete** on the watch page confirms, then `DELETE /videos/{id}`, then back to the library.

Website notes: [web/README.md](web/README.md).

### Check

```bash
cd backend && uv run pytest
cd web && npm test
```

---

## Read in this order

Start with the [phase map](docs/12-build-phases.md). Product *why* is docs 01–11. How the code is hosted is [13](docs/13-implementation-pass.md). The full index is [docs/README.md](docs/README.md).

| Doc | What it is |
|---|---|
| [docs/01-goal-and-context.md](docs/01-goal-and-context.md) | What this is, why it exists |
| [docs/02-conversation-summary.md](docs/02-conversation-summary.md) | Early thread, compressed (history) |
| [docs/03-key-decisions.md](docs/03-key-decisions.md) | Locked choices — **matches the 13 phases** |
| [docs/04-what-we-rejected.md](docs/04-what-we-rejected.md) | What we are not doing |
| [docs/05-architecture.md](docs/05-architecture.md) | Ingest vs question loop |
| [docs/06-tools.md](docs/06-tools.md) | JSON actions our Python runs |
| [docs/07-models-and-indexes.md](docs/07-models-and-indexes.md) | E4B, Whisper, SigLIP, CLAP, ColQwen, Postgres |
| [docs/08-frontend-backend.md](docs/08-frontend-backend.md) | FastAPI + Start + Video.js |
| [docs/09-implementation-plan.md](docs/09-implementation-plan.md) | Pointer to the 13 phases |
| [docs/10-references.md](docs/10-references.md) | Google posts, model cards, papers |
| [docs/11-glossary.md](docs/11-glossary.md) | Words |
| [docs/12-build-phases.md](docs/12-build-phases.md) | **Build order — phases 1–13 locked** |
| [docs/13-implementation-pass.md](docs/13-implementation-pass.md) | Libraries, Modal, size — **locked** |
| [docs/14-from-idea-to-production.md](docs/14-from-idea-to-production.md) | How to run agents without reading code |
| [docs/phases/](docs/phases/phase-01.md) | One brief per phase |

---

## What this is not

- Not a new video foundation model
- Not VLM captioning of every second at ingest
- Not “answer from the index only”
- Not native Gemma `tools=` (we own the JSON loop)
- Not Node-on-laptop as the API
- Not training Gemma E2B into CLIP for v1

Shipped caps live in `backend/app/tools/caps.py` and `backend/app/agent/schema.py`: **12 photos** per look, **30 seconds** of audio per listen, **12** JSON rounds, **60 seconds** per export. Oversize is refused, not silently shrunk. The early phase cards said 64 photos and 8 rounds; the live loop tightened the look and gave the model more rounds.

There is no license file yet. Until one is added, do not treat this as free to reuse.
