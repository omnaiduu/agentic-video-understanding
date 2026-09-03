# Implementation plan

Order. Don’t skip to captioning or E2B training.

## 1. Skeleton

- FastAPI + ffmpeg `get_meta` / `get_frames` / `get_audio` on a local mp4
- Gemma 4 (E4B is fine to wire tools; **quality default 12B**) with tool calling
- Hard caps on window + FPS
- Prove: “what happens at 0:10?” using **only** `get_frames` (no index)

## 2. Speech cache

- faster-whisper ingest → SQLite FTS
- `search_transcript`
- Prove: lecture question without sending the whole video

## 3. Visual cache

- SigLIP 2 @ 1 FPS → sqlite-vec/FAISS
- `search_visual`
- Prove: silent “red light” / “bird” without Gemma-skimming 2h

## 4. Audio cache

- CLAP or GLAP on 1–5s chunks
- `search_audio`
- Prove: “when did the bird make a sound?”
- Count path: merge hits + Python count

## 5. Export

- `export_clip` / `export_audio` → storage URL
- Duration cap

## 6. UI

- Upload, status, chat, timestamps, links
- Empty / error / loading

## 7. Multi-turn + polish

- Session memory of last times
- Optional `crop_frame` if tiny objects fail
- Optional `ocr_frame` if slides fail
- Optional PE Core / GLAP swap if retrieval is weak

## Not in this sequence

VLM ingest, scene detect, E2B embedder training, OCR-all-frames, desktop super-agent.

## Done when

A ≥10 minute video answers: (a) a speech question, (b) a silent visual question, (c) a sound question, (d) a follow-up without re-ingest, (e) an exported clip URL — without loading the whole file into Gemma.
