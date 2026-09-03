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
| Speech | **faster-whisper / Whisper** | `search_transcript` |
| Pictures | **SigLIP 2** (not 2021 CLIP as default) | `search_visual` |
| Sounds | **LAION-CLAP or GLAP** | `search_audio` |

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

- API: **Python FastAPI**
- Cut media: **ffmpeg**
- Serve Gemma: **Modal** (vLLM / whatever they already run)
- Store: **SQLite** (transcript, sessions) + **FAISS or sqlite-vec** + **S3/R2/Modal Volume** (videos, exports)
- UI: simple web app (upload, ingest status, chat, timestamps, clip links) — see frontend doc; framework not sacred

## Explicitly not v1

Scene detect · VLM captions / `search_notes` · OCR every frame · answering from RAG only · homemade E2B embedder · kitchen-sink desktop tools · dumping 2h into Gemma
