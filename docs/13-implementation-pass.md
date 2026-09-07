# Implementation pass — how, not what

**Status: OPEN.** Phases 1–13 are locked as **product**. This file is the **coding-agent** layer: packages, folders, Modal/GPU, how small to keep it.

You do not read the code. If this file is empty, an agent will invent GPUs, dump 2k-line modules, and pick extra libraries. Talk through this. Then we append a short **card** onto each phase brief.

Related: [phase map](12-build-phases.md) · [hosting notes](08-frontend-backend.md) · [Gemma sizes](07-models-and-indexes.md) · [from idea to production](14-from-idea-to-production.md) (the method: contracts, checks, stop)

---

## Why the first pass felt abstract

The 13 phases locked **jobs** (hold a file, cut, loop, search, UI, slides). Questions were “Postgres or SQLite?”, “click to seek?”.

They did **not** lock:

- Exact **libraries** and **why that one** (Vite vs TanStack Start changes the error surface).
- **Methods** (FastAPI `BackgroundTasks` vs a Modal function vs a queue).
- **Modal.com** GPU, scale-to-zero, one box vs two.
- **Size**: a phase should be a handful of files, not a generated novel.

That was a miss for a human who plans with agents and never opens the diff.

---

## Rule for coding agents (once locked)

- Follow the phase brief **and** that phase’s card here.
- Do **not** add a library that is not on the card.
- Do **not** put Whisper/SigLIP/CLAP/ColQwen/Gemma in TanStack Start server functions.
- Prefer **small modules** (one job per file). If a file is growing past ~200–300 lines, split. Do not “just generate more.”
- FakeBrain / mock Query in tests. No GPU in CI.

---

## What is already locked (do not reopen)

| Piece | Locked |
|---|---|
| API | FastAPI + SQLModel + **Postgres** + pgvector |
| Cut | ffmpeg CLI, 64 photos / 30s audio, 60s export |
| Brain | Gemma 4 **E4B** default, vLLM **JSON schema**, our state machine |
| Speech | faster-whisper turbo, hybrid FTS + E5 |
| Pictures | SigLIP 2 `so400m-patch16-384` |
| Slides | ColQwen2.x on unique frames; `search_slides` |
| Sound | LAION-CLAP, 3s / 1.5s hop |
| UI | TanStack Start, shadcn, Tailwind, TanStack Query, Video.js |
| Files | Local disk `data/videos/{id}/` (S3 later behind same functions) |

---

## What we still must lock (talk)

### A. Where things run

**Three jobs, three possible boxes**

1. **API** — FastAPI (upload, chat HTTP, Postgres).
2. **Brain** — vLLM serving Gemma (GPU, question time).
3. **Ingest** — Whisper + SigLIP + CLAP + ColQwen (GPU or CPU, once per file). ffmpeg can stay CPU.

If chat and a 2h ingest share **one small GPU**, chat dies while indexing. Older docs said split them ([07](07-models-and-indexes.md)).

| Option | What it is | When |
|---|---|---|
| **1. Laptop only** | API + ffmpeg + Postgres local. Gemma on a local GPU or skip (FakeBrain). | Writing the app, no Modal bill. |
| **2. API local, Gemma on Modal** | You run FastAPI at home. Chat calls Modal vLLM. Ingest local or Modal. | Cheap while coding UI. |
| **3. Everything on Modal** | FastAPI + Volume for files + vLLM + ingest jobs. Scale to zero. | Demo on the internet. |

**GPU for E4B (4-bit ~4.5 GB):** an **L4 (24 GB)** is enough and cheaper. **A10** is fine. **A100** is overkill for E4B. 12B later → 24 GB happier.

**Ingest GPU:** same L4 as a **second** Modal function (not the vLLM replica), or CPU if you accept slow SigLIP. Do not run 2h Whisper on the vLLM worker.

### B. How ingest is started (method)

| Option | What it is |
|---|---|
| **FastAPI BackgroundTasks** | Simple. Dies if the API process restarts mid-Whisper. OK for laptop. |
| **Modal function `.spawn()`** | Survives; right for Modal ingest. |
| **Redis/Celery queue** | Extra box. Not unless we have many users. |

Laptop: BackgroundTasks. Modal: spawn. Same Python `ingest_video(id)` function either way.

### C. Size budget (so agents don’t write thousands of lines)

Per phase, a coding agent should add **about this much**, not a framework:

| Phase | Rough new files | Stay out |
|---|---|---|
| 1 | `main.py`, `models.py`, `db.py`, `media/probe.py`, routes | No torch |
| 2 | `tools/frames.py`, `audio.py`, `caps.py` | No HTTP extras |
| 3 | `agent/loop.py`, `client.py`, `schema.py` | No `tools=` |
| 4–6 | `ingest/*.py`, `search/*.py`, one table each | No extra vector DBs |
| 7 | `tools/export.py` | No S3 SDK yet |
| 8 | session fields on existing chat | No Redis |
| 9 | Start scaffold + 2 routes + `lib/api.ts` | No extra UI kits |
| 10–12 | grow those routes | No new app |
| 13 | `ingest/slides.py`, `search/slides.py`, `SlidePage` | No OCR-all-frames; no extra vector DB |

If the agent needs a new library, **stop and ask**.

---

## Questions (answer these — this is the “bottom”)

**Hosting**

1. **Where does FastAPI live for the first real run?** laptop · Modal web · both (laptop dev, Modal later)?
2. **Where does Gemma live?** local vLLM · **Modal vLLM** · Ollama (weaker multimodal)?
3. **Chat GPU?** **L4** · A10 · A100. I would take **L4** for E4B, scale to zero.
4. **Ingest?** **Separate Modal function** (same GPU type, not the chat replica) · same process as API (laptop) · CPU only.

**Ingest method**

5. **Laptop = BackgroundTasks, Modal = `.spawn()` on the same `ingest_video` function.** OK?

**Size**

6. **Small files (~200–300 lines), no extra libraries without asking.** OK?

When these are answered, we write a **card** under each phase (packages + folder + Modal bits) so a coding agent has the bottom without you reading code.

Do **not** implement from this file until it says LOCKED and the cards exist.
