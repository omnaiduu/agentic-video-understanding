# What we rejected (and why)

| Idea | Why not (for v1 / as the spine) |
|---|---|
| **Static 1 FPS whole video into Gemma** | Cost scales with duration; Gemma 4 ~60s video gulp; misses sub-second events unless FPS is high everywhere |
| **New video foundation model** | Google didn’t ship one; they shipped a **tool loop** |
| **Whisper describes scenes / slides** | Whisper has **no eyes** |
| **VLM caption every few seconds (`search_notes`)** | Thousands of LLM calls at ingest; we already have specialists + Gemma at query time |
| **Answer only from the index** | Captions and embeddings lie; Google still **opens frames** |
| **PySceneDetect as core** | Finds **cuts**, not “red light” or “bird.” Optional later to skip duplicate lecture slides |
| **OpenAI CLIP as the visual encoder** | Works as a tutorial; **SigLIP 2** is the stronger default (Apache-2.0) |
| **Pixel CLIP as the only visual story** | Doesn’t **read** “Pro $99”; that’s Gemma on frames after a time is known |
| **OCR every frame at ingest** | Expensive; OCR **one** fetched frame later if the brain misreads slides |
| **No visual index, Gemma skims 2h** | Correct Google-like logic, **slow/$** on long CCTV every question |
| **No audio index** | Cannot do “bird chirp” / claps without chewing hours of audio in Gemma |
| **Clap-only detector as the audio design** | Too narrow; **`search_audio`** covers chirps, beeps, claps; detector only if counting ovations fails |
| **Train Gemma E2B as CLIP/CLAP** | Possible on Modal with data; **worse efficiency**. Fine-tune **CLAP** on domain data first |
| **MediaBunny as the backend cutter** | Fine in **browser**; server path is still FFmpeg. **ffmpeg CLI** for v1 |
| **Node as the ML API** | Whisper/SigLIP/Gemma live in **Python**. FastAPI is the API. (An earlier PR tried Node-on-laptop. Not this app.) |
| **Native Gemma `tools=` / OpenAI function calling** | Tool messages often drop image/audio. E4B is weak at multi-step tools. We own JSON + multimodal parts. |
| **Gemma 12B as the default brain** | We own the loop, so E4B is enough. 12B is an env switch later. |
| **SQLite + FAISS as the store** | One **Postgres + pgvector** for rows, keyword search, and vectors. |
| **Vite SPA / Next.js as the UI kit** | **TanStack Start** + shadcn + Query. Browser still talks only to FastAPI. |
| **WhisperX + three-speed form driver + Node API** | Other draft PRs. Not merged. Speech is faster-whisper turbo + hybrid FTS/E5. API is FastAPI. |
| **Replace SigLIP with ColQwen** | Different questions. SigLIP finds bird / red light. ColQwen2.x finds printed text. **Both** ship (Phases 5 and 13) |
| **ColQwen on every 1 FPS frame** | Hundreds of vectors per page × thousands of twins. Dedup first; unique slides only |
| **Answer from ColQwen scores** | Embeddings lie. Gemma still **looks**. ColQwen only finds the time |
| **Gemma audio instead of Whisper for the full file** | Gemma audio ~**30s**; 2h lecture needs Whisper cache |
| **31B / 26B-A4B as the omni brain** | **No native audio** on those sizes |
| **Kitchen-sink desktop tools** (web, python, calendar) | Different product. Video loop first |
| **Full Agentic Vision (arbitrary Python on images)** | `crop_frame` is enough if tiny objects fail |
| **Graph DB / Elasticsearch on day one** | Postgres + pgvector is enough |

**ColQwen2.x + `search_slides` is the product** (Phase 13), not a rejected idea. Locked brief: [phase-13.md](phases/phase-13.md). For “which slide had **Pro $99**?” when nobody said the number. Gemma still reads the real frame; ColQwen only finds the time.
