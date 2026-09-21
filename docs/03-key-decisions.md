# Key decisions

Locked. Short. This file matches the **13 build phases**. Do not follow older SQLite / 12B-default / native-tools drafts.

## Product

- Clone **Google agentic video**: Think → Act → Observe on a timeline.
- **Our Python loop + Gemma JSON** is the product. **Indexes** are caches.
- Cover **talk, silent visual, on-screen slide text, sound, many questions on one file, export clip, website**.

## Brain (question time only)

- **Gemma 4 E4B** = default. It **fills a JSON form**. It does not drive OpenAI-style `tools=`.
- **12B Unified** = env switch later if we want a stronger planner. Not the default.
- Do **not** use **Gemma** to index the whole video (no caption diary). **ColQwen2.x** at ingest is a **retriever** on unique slides (Phase 13), not a captioner.
- How it sees media: image/audio **content parts**, not `tool` messages.

## Loop

- We own a state machine: `look` · `listen` · `search` · `search_visual` · `search_audio` · `search_slides` · `export_clip` · `export_audio` · `answer`.
- vLLM **JSON schema** (`response_format`), not native function calling.
- Caps: **64 photos or 30 seconds of sound** per look/listen. **8** rounds max. Export **60s**, reject oversize.
- Tests use a FakeBrain. No GPU in CI.

## Indexes (ingest once, cache)

| Channel | Model | JSON action |
|---|---|---|
| Speech | faster-whisper **turbo** + hybrid FTS + E5 | `search` |
| Pictures | **SigLIP 2** `so400m-patch16-384` @ 1 FPS | `search_visual` |
| Slides | **ColQwen2.x** on unique frames | `search_slides` |
| Sounds | **LAION-CLAP**, 3s / 1.5s hop | `search_audio` |

- Store: **PostgreSQL + pgvector** (one DB). Files on disk `data/videos/{id}/`.
- Second question must **not** rebuild indexes.
- Counting = **Python merge + `len()`**, not Gemma memory.

## Status (complete app)

- After save + ffprobe the file exists.
- Then ingest runs in the background. Overall `status` = **`processing`**, then **`ready`** (or `error`).
- Per book: `transcript_status` · `visual_status` · `audio_status` · `slides_status` (`skipped` if that channel does not apply).
- Website: poll until overall `ready`; **chat off until then**. Show a **spinner + four live lines** (speech, pictures, sounds, slides) while ingesting. Timed look via API may still work if someone curls early.
- Upload cap: **2 GB**.

## Stack

- API: **Python FastAPI** + SQLModel. Not Node.
- Cut media: **ffmpeg** CLI.
- Serve Gemma: **vLLM on Modal (L4)**. Laptop FastAPI. Ingest is a **separate** Modal worker. Cards in [13](13-implementation-pass.md).
- UI: **TanStack Start** + Tailwind + shadcn/ui + TanStack Query + **Video.js**. FastAPI is the only ML API.
- Auth: none for v1.

## Explicitly not v1

Scene detect · VLM captions / `search_notes` · OCR every frame · answering from RAG only · homemade E2B embedder · WhisperX / three-speed Node driver · kitchen-sink desktop tools · dumping 2h into Gemma

**ColQwen / `search_slides`:** **this app** (Phase 13). For “which slide had **Pro $99**?” when nobody said the number. Gemma still reads the real frame; ColQwen only finds the time. Do not replace SigLIP. Do not OCR every frame.
