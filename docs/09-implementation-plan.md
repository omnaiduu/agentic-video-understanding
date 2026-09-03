# Implementation plan

Order. Don’t skip to captioning or E2B training.

## 1. Skeleton

- FastAPI + ffmpeg `get_meta` / `get_frames` / `get_audio` on a local mp4
- Gemma 4 (E4B is fine to wire tools; **quality default 12B**) with tool calling
- Hard caps on window + FPS
- Short-file bypass later: duration ≲ 5 min may static-gulp (Google’s split)
- Prove: “what happens at 0:10?” using **only** `get_frames` (no index)

## 2. Speech cache

- faster-whisper ingest → SQLite FTS
- Prefer **WhisperX** (VAD + word alignment) so FTS hits have real start/end times — see [12-whats-new-2026.md](12-whats-new-2026.md)
- `search_transcript`
- Prove: lecture question without sending the whole video

## 3. Visual cache

- SigLIP 2 @ 1 FPS → sqlite-vec/FAISS
- Dedup consecutive near-duplicate frames (lecture slides)
- `search_visual`
- Prove: silent “red light” / “bird” without Gemma-skimming 2h

## 4. Audio cache

- **GLAP** default (LAION-CLAP only if GLAP is painful to install)
- 1–5s chunks
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

- Session memory of last times; **prefix / KV cache** so tool rounds do not re-prefill
- Short-file bypass: duration ≲ 5 min may static-gulp (Google’s own split)
- Optional `crop_frame` if tiny objects fail
- Optional `ocr_frame` **or ColQwen `search_slides`** if “what number on the slide?” fails
- Optional PE Core / clip-level embeddings if motion retrieval is weak
- Optional SAM2 `track_and_count` if object counting double-counts

## Not in this sequence

VLM ingest, scene detect, E2B embedder training, OCR-all-frames, desktop super-agent.

## Done when

A ≥10 minute video answers: (a) a speech question, (b) a silent visual question, (c) a sound question, (d) a follow-up without re-ingest, (e) an exported clip URL — without loading the whole file into Gemma.
