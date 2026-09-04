# Agentic Video Understanding (open-source)

An open-source system that copies **Google Gemini’s agentic video understanding** (announced 1 Sep 2026): a model with a remote control on a video timeline, not a model that watches every second.

This repository is the **design, decisions, and conversation record**. Implementation code is not in this repo yet.

**If you are a human:** [HUMAN-backend.md](HUMAN-backend.md) (picture) · [HUMAN-data.md](HUMAN-data.md) (contract) · [HUMAN-locked.md](HUMAN-locked.md) (what you decided). Numbered `docs/` files are for coding agents.

**Goal:** Ask questions about long videos (talks, slides, sports, CCTV, sounds) without dumping the whole file into a large model. Find the moment, look or listen to a short slice, then answer — optionally export a clip with a link.

---

## Read in this order

| Doc | What it is |
|---|---|
| [docs/01-goal-and-context.md](docs/01-goal-and-context.md) | What this is, why it exists, what we realized |
| [docs/02-conversation-summary.md](docs/02-conversation-summary.md) | Full thread, compressed — no extra commentary |
| [docs/03-key-decisions.md](docs/03-key-decisions.md) | Locked choices in short form |
| [docs/04-what-we-rejected.md](docs/04-what-we-rejected.md) | What we are not doing, and why |
| [docs/05-architecture.md](docs/05-architecture.md) | How the system works |
| [docs/06-tools.md](docs/06-tools.md) | Tools the bot gets |
| [docs/07-models-and-indexes.md](docs/07-models-and-indexes.md) | Gemma, Whisper, SigLIP, CLAP |
| [docs/08-frontend-backend.md](docs/08-frontend-backend.md) | Stack, hosting (Modal), data stores |
| [docs/09-implementation-plan.md](docs/09-implementation-plan.md) | Build order |
| [docs/10-references.md](docs/10-references.md) | Google posts, model cards, papers |
| [docs/11-glossary.md](docs/11-glossary.md) | CLIP, VLM, FPS, RAG, etc. |
| [docs/12-whats-new-2026.md](docs/12-whats-new-2026.md) | 2025–2026 techniques vs this design: keep, swap, refuse |
| [docs/13-whisperx.md](docs/13-whisperx.md) | Speech phone book: what WhisperX is, why, how VAD/aligner/diarization work |
| [docs/14-slides-and-on-screen-text.md](docs/14-slides-and-on-screen-text.md) | Unique slides + ColQwen: find on-screen text, Gemma still reads |
| [docs/15-workflows-vs-agents.md](docs/15-workflows-vs-agents.md) | Code-owned paths + small E4B vs a 12B free agent |
| [docs/16-clipboard-and-verbs.md](docs/16-clipboard-and-verbs.md) | Session clipboard + verb menu so combo questions work on E4B |
| [docs/17-plain-map.md](docs/17-plain-map.md) | One-page map: books vs tools vs 12B vs 4B |
| [docs/18-the-plan.md](docs/18-the-plan.md) | Short plan: small Gemma fills a form (intent + verbs), code runs tools |
| [docs/19-three-speeds.md](docs/19-three-speeds.md) | Ready-made job + many intents + short hunt, still E4B |
| [docs/20-backend-algorithm.md](docs/20-backend-algorithm.md) | How the backend runs: Node local, Modal models, step-by-step logic |

---

## One-sentence product

**Gemma 4 (brain, question time only) + ffmpeg (scissors) + three phone books built once: WhisperX (speech), SigLIP 2 (pictures), GLAP (sounds).**

---

## What this is not

- Not a new video foundation model
- Not VLM captioning of every second at ingest
- Not “answer from the index only”
- Not training Gemma E2B into CLIP for v1

---

## Environment note

Docs were written in a **Linux cloud agent**, not Windows WSL. Clone this repo onto your WSL machine to work locally. Publishing to **GitHub** needs your GitHub login (this environment has no `gh` auth).
