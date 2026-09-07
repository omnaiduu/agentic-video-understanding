# Key decisions

Locked. Short. This file matches the **12 build phases**. Do not follow older SQLite / 12B-default / native-tools drafts.

## Product

- Clone **Google agentic video**: Think → Act → Observe on a timeline.
- **Our Python loop + Gemma JSON** is the product. **Indexes** are caches.
- Cover **talk, silent visual, sound, many questions on one file, export clip, website**.

## Brain (question time only)

- **Gemma 4 E4B** = default. It **fills a JSON form**. It does not drive OpenAI-style `tools=`.
- **12B Unified** = env switch later if we want a stronger planner. Not the default.
- Do **not** use the VLM to index the whole video.
- How it sees media: image/audio **content parts**, not `tool` messages.

## Loop

- We own a state machine: `look` · `listen` · `search` · `search_visual` · `search_audio` · `export_clip` · `export_audio` · `answer`.
- vLLM **JSON schema** (`response_format`), not native function calling.
- Caps: **64 photos or 30 seconds of sound** per look/listen. **8** rounds max. Export **60s**, reject oversize.
- Tests use a FakeBrain. No GPU in CI.

## Indexes (ingest once, cache)

| Channel | Model | JSON action |
|---|---|---|
| Speech | faster-whisper **turbo** + hybrid FTS + E5 | `search` |
| Pictures | **SigLIP 2** `so400m-patch16-384` @ 1 FPS | `search_visual` |
| Sounds | **LAION-CLAP**, 3s / 1.5s hop | `search_audio` |

- Store: **PostgreSQL + pgvector** (one DB). Files on disk `data/videos/{id}/`.
- Second question must **not** rebuild indexes.
- Counting = **Python merge + `len()`**, not Gemma memory.

## Status (complete app)

- After save + ffprobe the file exists.
- Then ingest runs in the background. Overall `status` = **`processing`**, then **`ready`** (or `error`).
- Per book: `transcript_status` · `visual_status` · `audio_status` (`skipped` if that channel does not apply).
- Website: poll until overall `ready`; **chat off until then**. Timed look via API may still work if someone curls early.
- Upload cap: **2 GB**.

## Stack

- API: **Python FastAPI** + SQLModel. Not Node.
- Cut media: **ffmpeg** CLI.
- Serve Gemma: **vLLM** (laptop or Modal — hosting cards still **open** in [13](13-implementation-pass.md)).
- UI: **TanStack Start** + Tailwind + shadcn/ui + TanStack Query + **Video.js**. FastAPI is the only ML API.
- Auth: none for v1.

## Explicitly not v1

Scene detect · VLM captions / `search_notes` · OCR every frame · answering from RAG only · homemade E2B embedder · WhisperX / three-speed Node driver · kitchen-sink desktop tools · dumping 2h into Gemma

**ColQwen / `search_slides`:** not v1. Full design lives in [what we rejected](04-what-we-rejected.md) as a later alternative if printed slide text fails.
