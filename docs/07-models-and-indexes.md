# Models and indexes

## Brain — Gemma 4 E4B default

| | **E4B (default)** | **12B Unified (later switch)** |
|---|---|---|
| Modalities | Text, image, audio | Text, image, audio |
| Role | Fills JSON; we own the loop | Stronger planner if we need it |
| Native tools | Weak (Tau2 ~42%) — **we do not use them** | Better, still not our path |
| Video gulp | ~60s @ 1 FPS (card) | same class of limit |
| Audio gulp | ~30s | ~30s |
| Memory (4-bit, weights) | ~4.5 GB | ~6.7 GB |
| Comfortable GPU | **L4 (24 GB) is enough** | 16 GB min, 24 GB happier |

**12B is not “no VLM.”** Official card: E2B, E4B, **and 12B Unified** all take image + audio. 31B and 26B-A4B are vision+text **without** audio — don’t pick those as the omni brain.

**Cost (order of magnitude, Modal public rates ~2026):** L4 ~$0.80/hr, A10 ~$1.10/hr. Idle on Modal ≈ $0 if scaled to zero.

**Qwen3-VL 8B:** often stronger **eyes/OCR**; **no native audio**. Not the locked brain.

Gemma **does not** replace Whisper for a 2-hour transcript.

## Speech index — Whisper + hybrid text RAG

- **faster-whisper turbo** once per file → `{t, text}` (model name swappable)
- **Keyword:** Postgres `tsvector` + GIN
- **Meaning:** E5-small (or MiniLM via config) → pgvector
- **Merge:** Reciprocal Rank Fusion, top ~8
- This is **speech words**, not a scene log. Not WhisperX. Not a speech-audio embedder.

## Picture index — SigLIP 2

- CLIP-**style**, not a chatbot
- ~1 photo/sec → `VisualFrame` in **pgvector**
- Default: `google/siglip2-so400m-patch16-384`
- Query: embed the **phrase**, nearest times
- Delete bulk JPEGs after embed
- **Why not 2021 CLIP:** SigLIP 2 is stronger, multilingual, Apache-2.0
- **PE Core (Meta):** optional later, same table + action
- **Not hybrid:** pictures have no words. No caption-every-second.

## Slide index — ColQwen2.x

- Patch-level retriever (ColPali family), not a chatbot
- Run on **unique slides** after dedup (pHash and/or SigLIP vs last kept frame), not every 1 FPS copy
- Default: **ColQwen2.x** (vidore ColQwen2 / 2.5; name in config). Fallback ColPali
- Query: text tokens → MaxSim vs patches → times
- Chat action: **`search_slides`**
- **Gemma still reads the real frame. ColQwen only finds the time.**
- For “which slide had **Pro $99**?” when nobody **said** the number
- **Does not replace SigLIP.** Birds / red lights stay `search_visual`
- Store: `SlidePage` in the same **Postgres + pgvector**

## Sound index — CLAP family

- **LAION-CLAP** default (`laion/larger_clap_general` or `clap-htsat-fused`; name in config)
- **GLAP** later, same table, same `search_audio`
- Chunk **3s**, hop **1.5s** → `AudioChunk` in pgvector
- **Still needed if SigLIP exists:** chirps, claps, beeps are **not** in the picture index

CLAP **finds**. It does **not** answer. Counting = threshold + merge + `len()`.

## What we do not train for v1

Turning **E2B into an embedding model**. If we have domain labels, **fine-tune CLAP**, don’t promote the brain to phone book.

## Hosting

Exact laptop vs Modal split is **locked** in [13](13-implementation-pass.md):

- Laptop: FastAPI, Postgres, files, ffmpeg.
- Modal: Gemma (chat worker) and ingest (other worker). **L4.** Slices only. Scale to zero.
- Don’t put 2h ingest and the chat loop on one running GPU replica.
