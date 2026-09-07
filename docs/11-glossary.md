# Glossary

| Term | Meaning here |
|---|---|
| **LLM** | Text model. Today often multimodal. |
| **VLM** | Model that can **see** pictures (Gemma 4). **Brain at question time only.** |
| **Agentic** | Loop: think → our code acts → look at results → repeat → answer |
| **State machine** | Our Python owns look/listen/search/export/answer. Gemma only fills JSON. |
| **Structured output** | vLLM forces a JSON schema. Not “please reply in JSON.” |
| **Static processing** | Fixed FPS dump of the whole video into the model |
| **Pass-by-reference** | Send file id + duration, not all frames |
| **FPS** | Photos per second. High = see fast motion, costs more |
| **Whisper** | Speech → text + times. No vision. We use faster-whisper **turbo**. |
| **Transcript** | Whisper output |
| **CLIP / SigLIP** | Picture and text → vectors; **search**, don’t narrate |
| **Index / phone book** | Saved search (transcript / visual vectors / audio vectors) |
| **Ingest** | Build indexes **once** per video |
| **Cache** | Reuse ingest; don’t Whisper again on question 2 |
| **CLAP** | CLIP-for-**audio**; sound ↔ text search |
| **RAG** | Retrieve then generate. Search finds times; Gemma still **verifies** |
| **Hybrid search** | Keyword (Postgres FTS) + meaning (E5) + RRF. Speech only. |
| **ffmpeg** | Cut/decode video and audio |
| **JSON action** | What Gemma writes (`look`, `search`, …). We run the function. |
| **Export** | Write a clip/audio to disk and return a GET URL |
| **Agentic Vision** | Zoom/crop **inside one still** (Google). Not the video timeline |
| **search_notes** | Search VLM **captions** from ingest. **We don’t do this** |
| **Modal** | GPU host we may use for Gemma / ingest (hosting still open in doc 13) |
| **E4B / 12B** | Gemma 4 sizes. **E4B = default.** 12B = later env switch. |
| **ColQwen / ColPali** | Patch-level slide retriever (MaxSim). **This app** (Phase 13). `search_slides`. Gemma still reads the real frame; ColQwen only finds the time. |
| **search_slides** | JSON action: find a unique slide by on-screen text (“Pro $99”). |
