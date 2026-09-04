# Key decisions

Locked. Short.

## Product

- Clone **Google agentic video**: Think → Act → Observe on a timeline.
- **Brain + tools** is the product. **Indexes** are caches.
- Cover **talk, silent visual, sound, slides (ColQwen), many questions on one file, export clip**.
- Demo: **one user**, **English**, **mp4** (file or URL), **audio-only OK**, **one chat = one video**.
- **No login.** Refresh clears the chat. Files stay on the owner’s disk.
- Empty search → **“couldn’t find it”** (never guess).
- UI: spinner + **live status**, answer shows **transcript quote + frame(s)** + timestamps.

## Brain (question time only)

- **Gemma 4 E4B only** for the demo (plan form + read slice). **No 12B fallback.**
- Do **not** use the VLM to index the whole video.

## Indexes (ingest once, cache)

| Channel | Model | Tool |
|---|---|---|
| Speech | **WhisperX** (English; word times; **diarization on** for Speaker 1/2 — drop if it blows the $30 budget) | `search_transcript` |
| Pictures | **SigLIP 2** | `search_visual` |
| Sounds | **GLAP** | `search_audio` |
| Slides | **ColQwen** (required; ColPali fallback) on unique frames | `search_slides` |

- Sample pictures at ~**1 FPS** for the visual index.
- Chunk audio ~**1–5s** for the audio index.
- Second question must **not** rebuild indexes.

## Tools (v1)

`get_meta` · `search_transcript` · `search_visual` · `search_audio` · `search_slides` · `get_frames` · `get_audio` · `export_clip` · `export_audio`

- Frame **budget** (cap how many frames Gemma sees per question).
- Export **max length** (e.g. 60s).
- Answers from **rewatch**, not from search scores alone.
- Counting = **search hits + merge + count in code**.

## Stack

- API (demo): **Node** on the laptop — traffic cop (form, three speeds, notepad, ffmpeg). See [20](20-backend-algorithm.md).
- ML workers: **Python on Modal**, deploy **from zero** — Gemma E4B, WhisperX, SigLIP 2, GLAP, **ColQwen**. Target ~**$30/mo**, scale to zero.
- Cut media: **ffmpeg** on the laptop; source mp4 **on the owner’s disk**
- Session: **in memory** (refresh clears chat). No login.
- UI: **one page**, desktop first; spinner + live status; quote + frame in the answer

(Older lock was “Python FastAPI for everything.” Demo split: Node orchestrates, Modal stays Python for models.)

## Explicitly not v1

Scene detect · VLM captions / `search_notes` · OCR every frame · answering from RAG only · homemade E2B embedder · kitchen-sink desktop tools · dumping 2h into Gemma

## After the Sep 2026 review

Practical defaults that do **not** fork the product: **GLAP**; **WhisperX**; **dedup** lecture frames; **ColQwen required**. Survey: [12-whats-new-2026.md](12-whats-new-2026.md).

**Demo driver (locked for this ship):** E4B form + notepad + three speeds + live status. Human summary: [HUMAN-locked.md](../HUMAN-locked.md).
