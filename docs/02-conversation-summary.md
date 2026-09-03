# Conversation summary

Compressed record of the design thread. Not a transcript.

## Start

User asked how **Google agentic video understanding** works, in simple words, then technically, then how to build an open-source version.

**Google (public):** same Flash models, `processing: "agentic"`. Pass-by-reference. Server-side tools: transcript-first, temporal crop + adaptive FPS, audio slice. Think → Act → Observe. Pay for materialized slices. Analogous to **Agentic Vision** (zoom/crop a still via code) but on a **timeline**.

## Early design noise

A “v0 / v1 / v2” split (scene detect, CLIP+FAISS, frame budgets, `step_list`) was too many versions. User asked for **one** system and suggested: multimodal LLM writes transcript + screen notes with timestamps, embed, retrieve. **Scene detect dropped** as a required piece (correct — cuts ≠ red light).

## Correction: Whisper is not a camera

User thought Whisper should also output scene + on-screen text. **No.** Whisper = speech. Screen = VLM **looking at frames** at question time (or optional expensive captions we later dropped). Silent visual needs **eyes** (SigLIP index and/or Gemma skim).

## Two options, then one product

- **Option 1 — ingest library:** Whisper + visual (and later audio) embeddings once.
- **Option 2 — agent tools:** get frames/audio, search indexes, skim/zoom.

**Locked:** Option 2 is the product. Option 1 is how tools stay fast. Not two apps.

## CLIP explained

CLIP/SigLIP: picture and text → same number-space. **Index** = 1 FPS vectors + times. Query “flying bird” → timestamps in milliseconds. **Not** a narrator. Visual RAG = retrieve then Gemma verifies.

No-index skim of 2h CCTV is slow because **Gemma** would ingest hundreds of frames per question. CLIP-class ingest uses a **tiny** encoder once.

## Stack and hosting

- Brain: **Gemma 4** (user: E4B / 12B). 12B **does** have vision+audio (E2B, E4B, **12B Unified**). 31B / 26B-A4B = no audio.
- 12B is the better **tool caller**; E4B is cheaper and weaker on multi-step tools.
- Host models on **Modal** (user said “model.com”).
- Backend: **Python + FastAPI + ffmpeg**. MediaBunny = optional JS/browser; still FFmpeg underneath.
- DB: SQLite + vectors (sqlite-vec or FAISS) + object storage for files/exports.

## Export

User: bot should **cut a slice**, maybe audio, upload storage, **return a link**. Locked as `export_clip` / `export_audio`. Cap duration.

## Optional tools (mostly deferred)

- **Agentic Vision** = crop/zoom **inside one photo** (Google: Python on an image). Our cheap version: `crop_frame`. Easy later.
- **`search_notes`** = search VLM **written** captions. **Not our plan** (no VLM at ingest). User called this out; extras were mixing the story.
- **`ocr_frame`** = OCR **one** already-opened frame. Not OCR every frame. Later if slides fail.

## Audio channel

Counting **claps** in 2h: Gemma cannot hear 2h. Whisper won’t transcribe claps. Image index won’t hear claps.

**Locked pattern:** audio embeddings (**CLAP / GLAP**) + `search_audio`, same as SigLIP for pictures. Count in **Python** on hits. A clap-only detector is optional if CLAP merges ovations badly.

User: “when did the bird make a sound?” → **needs audio index**. Image index finds a **visible** bird, not a **chirp**.

## Do not train E2B into CLIP

Possible as research (contrastive LoRA on Modal; Omni-Embed-Audio did this with a 3B omni LLM). **v1: no.** E2B-per-chunk is the expensive phone book. Fine-tune CLAP on domain data if needed, not E2B.

## This docs repo

User asked for a local WSL repo with plans, decisions, conversation context, frontend/backend, references — concise and clear — and GitHub if possible.
