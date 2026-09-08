# Agentic Video Understanding (open-source)

An open-source system that copies **Google Gemini’s agentic video understanding** (announced 1 Sep 2026): a model with a remote control on a video timeline, not a model that watches every second.

This repository is the **design, decisions, and conversation record**, plus **Phases 1–9** of the app (`backend/` through memory, `web/` library + watch-and-ask shell). Upload, player, and chat UI are not in this slice.

**To start code:** [docs/13-implementation-pass.md](docs/13-implementation-pass.md) (how) + the matching [docs/phases/](docs/phases/phase-01.md) brief. One phase only. API runbook: [backend/README.md](backend/README.md). Website: [web/README.md](web/README.md).

**Source of truth:** the **13 locked build phases**. If an older paragraph says SQLite, Gemma 12B as default, native `tools=`, Vite-only UI, or Node backend — ignore it. Those were earlier drafts. They are not this app.

**Goal:** Ask questions about long videos (talks, slides, sports, CCTV, sounds) without dumping the whole file into a large model. Find the moment, look or listen to a short slice, then answer — optionally export a clip with a link.

---

## One-sentence product

**Gemma 4 E4B (fills a JSON form) + our Python loop + ffmpeg (scissors) + four phone books built once: Whisper (speech), SigLIP 2 (pictures), CLAP (sounds), ColQwen2.x (slides) + a TanStack Start website.**

ColQwen2.x and `search_slides` are for questions like “which slide had **Pro $99**?” when nobody said the number. Gemma still reads the real frame; ColQwen only finds the time.

---

## Read in this order

Start with the [phase map](docs/12-build-phases.md). Product *why* is docs 01–11. How a coding agent writes code is [13](docs/13-implementation-pass.md) (**locked**). Code so far is in `backend/` (Phases [1](docs/phases/phase-01.md)–[8](docs/phases/phase-08.md)) and `web/` ([Phase 9](docs/phases/phase-09.md)).

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

---

## Environment note

Docs were written in a **Linux cloud agent**. Clone this repo to work locally.
