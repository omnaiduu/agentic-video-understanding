# Models and indexes

## Brain — Gemma 4 only (locked family)

| | **E4B** | **12B Unified** |
|---|---|---|
| Modalities | Text, image, audio | Text, image, audio |
| Role | Cheap / QPS | **Default agent** |
| Tools | Weaker multi-step | Better planner |
| Video gulp | ~60s @ 1 FPS (card) | same class of limit |
| Audio gulp | ~30s | ~30s |
| Memory (4-bit, weights) | ~4.5 GB | ~6.7 GB |
| Comfortable GPU | 12–16 GB | **16 GB min, 24 GB happier** |

**12B is not “no VLM.”** Official card: E2B, E4B, **and 12B Unified** all take image + audio. 31B and 26B-A4B are vision+text **without** audio — don’t pick those as the omni brain.

**Cost (order of magnitude, Modal public rates ~2026):** L4 ~$0.80/hr, A10 ~$1.10/hr. 12B ≈ **2.5–3× compute per token** vs E4B; often **~2–4× cost per video question** (slower + more KV from frames). Idle on Modal ≈ $0 if scaled to zero.

**Qwen3-VL 8B:** often stronger **eyes/OCR**; **no native audio**. Not the locked brain; possible later A/B for `get_frames` only.

Gemma **does not** replace Whisper for a 2-hour transcript.

## Speech index — WhisperX (Whisper + clock)

- Run **WhisperX** once per file, not bare Whisper times — full why/how: [13-whisperx.md](13-whisperx.md)
- **faster-whisper** (large-v3 or turbo) = the typist inside WhisperX
- VAD + wav2vec2 **word-level** times for FTS, seek, and `export_clip`
- Diarization **off** in v1 (one speaker). Panels later.
- English-only speed/accuracy later: Parakeet / Canary as the typist; **same** `search_transcript` tool
- This is **elaborate speech**, not a scene log

## Picture index — SigLIP 2

- CLIP-**style**, not a chatbot
- ~1 photo/sec → vector → FAISS / sqlite-vec
- Query: embed the **phrase**, nearest times
- **Why not 2021 CLIP:** SigLIP 2 is stronger, multilingual, Apache-2.0
- **PE Core (Meta, 2025):** first swap if sports/CCTV retrieval is weak — beats SigLIP 2 on video benchmarks; same `search_visual` slot
- **Talks/slides:** SigLIP finds a slide, it does not read “Pro $99”. Optional later: ColQwen/ColPali on **deduped** frames (`search_slides`), then Gemma still rewatches
- **Cost:** 2h @ 1 FPS ≈ 7200 small forwards (minutes GPU / tens of minutes CPU), then queries in **ms**
- Storage: tens of MB of vectors, not the video again

## Sound index — CLAP family

- **GLAP** (Xiaomi, 2025) as the v1 default; LAION-CLAP only if GLAP is painful to install
- Stronger papers exist (M2D-CLAP, FineLAP, WavLink); **same tool API**, swap later
- Chunk 1–5s → vector + time
- **Still needed if SigLIP exists:** chirps, claps, beeps are **not** in the picture index

CLAP **finds**. It does **not** answer. Counting = threshold + merge + `len()`.

## What we do not train for v1

Turning **E2B into an embedding model** (PyTorch contrastive on Modal): valid research (see Omni-Embed-Audio on 3B omni LLMs). **Worse ingest cost** than SigLIP/CLAP. If we have domain labels, **fine-tune CLAP**, don’t promote the brain to phone book.

## Hosting (Modal)

Separate endpoints if needed:

1. Gemma chat (GPU, always-on or scale-to-zero)
2. Batch ingest: Whisper + SigLIP + CLAP
3. CPU ffmpeg export

Don’t put 2h ingest and the chat loop on one tiny GPU fighting each other.
