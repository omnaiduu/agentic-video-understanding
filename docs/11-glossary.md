# Glossary

| Term | Meaning here |
|---|---|
| **LLM** | Text model. Today often multimodal. |
| **VLM** | Model that can **see** pictures (Gemma 4). **Brain at question time only.** |
| **Agentic** | Loop: think → call tools → look at results → repeat → answer |
| **Static processing** | Fixed FPS dump of the whole video into the model |
| **Pass-by-reference** | Send file id + duration, not all frames |
| **FPS** | Photos per second. High = see fast motion, costs more |
| **Whisper** | Speech → text + times. No vision |
| **Transcript** | Whisper output |
| **CLIP / SigLIP** | Picture and text → vectors; **search**, don’t narrate |
| **Index** | Saved phone book (transcript / visual vectors / audio vectors) |
| **Ingest** | Build indexes **once** per video |
| **Cache** | Reuse ingest; don’t Whisper again on question 2 |
| **CLAP** | CLIP-for-**audio**; sound ↔ text search |
| **RAG** | Retrieve then generate. Our visual/audio search is RAG; Gemma still **verifies** |
| **ffmpeg** | Cut/decode video and audio |
| **Tool** | Function Gemma is allowed to call |
| **Export** | Write a clip/audio to storage and return a URL |
| **Agentic Vision** | Zoom/crop **inside one still** (Google). Not the video timeline |
| **search_notes** | Search VLM **captions** from ingest. **We don’t do this** |
| **Modal** | GPU host for Gemma / ingest (user: “model.com”) |
| **E4B / 12B** | Gemma 4 sizes. 12B = default agent |
