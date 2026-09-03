# Key decisions

Locked. Short.

## Product

- Clone **Google agentic video**: Think → Act → Observe on a timeline.
- **Brain + tools** is the product. **Indexes** are caches.
- Cover **talk, silent visual, sound, many questions on one file, export clip**.

## Brain (question time only)

- **Gemma 4 12B Unified** = default agent (text + image + short audio + tools).
- **Gemma 4 E4B** = cheaper / higher QPS; weaker multi-step tools.
- Do **not** use the VLM to index the whole video.

## Indexes (ingest once, cache)

| Channel | Model | Tool |
|---|---|---|
| Speech | **WhisperX** (faster-whisper + word times; diarization off for v1 talks) | `search_transcript` |
| Pictures | **SigLIP 2** (not 2021 CLIP as default) | `search_visual` |
| Sounds | **GLAP** (LAION-CLAP fallback) | `search_audio` |

- Sample pictures at ~**1 FPS** for the visual index.
- Chunk audio ~**1–5s** for the audio index.
- Second question must **not** rebuild indexes.

## Tools (v1)

`get_meta` · `search_transcript` · `search_visual` · `search_audio` · `get_frames` · `get_audio` · `export_clip` · `export_audio`

- Frame **budget** (cap how many frames Gemma sees per question).
- Export **max length** (e.g. 60s).
- Answers from **rewatch**, not from search scores alone.
- Counting = **search hits + merge + count in code**.

## Stack

- API (demo): **Node** on the laptop — traffic cop (form, three speeds, notepad, ffmpeg). See [20](20-backend-algorithm.md).
- ML workers: **Python on Modal** — Gemma E4B, WhisperX, SigLIP 2, GLAP (Node does not run these).
- Cut media: **ffmpeg** on the laptop
- Serve Gemma: **Modal**
- Store: **SQLite** (videos, chats, notepad) + books on Modal Volume; object storage for mp4/exports
- UI: one watch+ask page is enough to **record a demo**; Vite/React later if needed

(Older lock was “Python FastAPI for everything.” Demo split: Node orchestrates, Modal stays Python for models.)

## Explicitly not v1

Scene detect · VLM captions / `search_notes` · OCR every frame · answering from RAG only · homemade E2B embedder · kitchen-sink desktop tools · dumping 2h into Gemma

## After the Sep 2026 review

Spine above is unchanged. Practical defaults that do **not** fork the product: **GLAP** over LAION-CLAP; **WhisperX** word times around Whisper ([13-whisperx.md](13-whisperx.md)); **dedup** lecture frames. Optional later: ColQwen slides, PE Core, SAM2 count. Survey: [12-whats-new-2026.md](12-whats-new-2026.md).

**Open (not locked):** **E4B** fills a **form** from **user chat + notepad**; Node runs tools at one of three speeds — [18](18-the-plan.md), [19](19-three-speeds.md), [20](20-backend-algorithm.md).
