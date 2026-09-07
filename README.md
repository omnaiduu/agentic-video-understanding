# Agentic Video Understanding (open-source)

An open-source system that copies **Google Gemini’s agentic video understanding** (announced 1 Sep 2026): a model with a remote control on a video timeline, not a model that watches every second.

This repository is the **design, decisions, and conversation record**. Implementation code is not in this repo yet.

**Source of truth:** the **12 locked build phases**. If an older paragraph says SQLite, Gemma 12B as default, native `tools=`, Vite-only UI, Node backend, or ColQwen — ignore it. Those were earlier drafts. They are not this app.

**Goal:** Ask questions about long videos (talks, slides, sports, CCTV, sounds) without dumping the whole file into a large model. Find the moment, look or listen to a short slice, then answer — optionally export a clip with a link.

---

## One-sentence product

**Gemma 4 E4B (fills a JSON form) + our Python loop + ffmpeg (scissors) + three phone books built once: Whisper (speech), SigLIP 2 (pictures), CLAP (sounds) + a TanStack Start website.**

---

## Read in this order

Start with the [phase map](docs/12-build-phases.md). Product *why* is docs 01–11 (now aligned with the phases). How a coding agent writes code is [13](docs/13-implementation-pass.md) (**still open**: Modal/GPU cards).

| Doc | What it is |
|---|---|
| [docs/01-goal-and-context.md](docs/01-goal-and-context.md) | What this is, why it exists |
| [docs/02-conversation-summary.md](docs/02-conversation-summary.md) | Early thread, compressed (history) |
| [docs/03-key-decisions.md](docs/03-key-decisions.md) | Locked choices — **matches the 12 phases** |
| [docs/04-what-we-rejected.md](docs/04-what-we-rejected.md) | What we are not doing |
| [docs/05-architecture.md](docs/05-architecture.md) | Ingest vs question loop |
| [docs/06-tools.md](docs/06-tools.md) | JSON actions our Python runs |
| [docs/07-models-and-indexes.md](docs/07-models-and-indexes.md) | E4B, Whisper, SigLIP, CLAP, Postgres |
| [docs/08-frontend-backend.md](docs/08-frontend-backend.md) | FastAPI + Start + Video.js |
| [docs/09-implementation-plan.md](docs/09-implementation-plan.md) | Pointer to the 12 phases |
| [docs/10-references.md](docs/10-references.md) | Google posts, model cards, papers |
| [docs/11-glossary.md](docs/11-glossary.md) | Words |
| [docs/12-build-phases.md](docs/12-build-phases.md) | **Build order — phases 1–12 locked** |
| [docs/13-implementation-pass.md](docs/13-implementation-pass.md) | Libraries, Modal, size — **open** |
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

---

## Environment note

Docs were written in a **Linux cloud agent**. Clone this repo to work locally.
