# Glossary

| Term | Meaning here |
|---|---|
| **LLM** | Text model. Today often multimodal. |
| **VLM** | Model that can **see** pictures (Gemma 4). **Brain at question time only.** |
| **Agentic** | Loop: think → call tools → look at results → repeat → answer |
| **Static processing** | Fixed FPS dump of the whole video into the model |
| **Pass-by-reference** | Send file id + duration, not all frames |
| **FPS** | Photos per second. High = see fast motion, costs more |
| **Whisper** | Speech → text. No vision. Clock is sloppy alone |
| **WhisperX** | Factory: VAD + Whisper + **aligner** (word times) + optional **diarization** (who). See [13-whisperx.md](13-whisperx.md) |
| **Aligner** | Pins each known word onto the audio (karaoke / forced alignment). Does not fix wrong words |
| **Diarization** | Splits voices into Speaker 0 / 1. Not names. Off for one-person talks |
| **VAD** | Speech vs silence/noise so Whisper transcribes less junk |
| **Parakeet / Canary** | Other **typists** (English ASR). Not an aligner. Same `search_transcript` slot later |
| **Transcript** | Speech index we search |
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
| **ColPali / ColQwen** | Late-interaction search over **slide screenshots**, not OCR-all-frames |
| **PE Core** | Meta 2025 CLIP-class encoder; stronger video retrieval than SigLIP 2 |
| **Muon / SOAP** | Training optimizers for LLM pretrain. **Not** our ingest/question loop |
| **Modal** | GPU host for Gemma / ingest (user: “model.com”) |
| **E4B / 12B** | Gemma 4 sizes. 12B = default **agent**; E4B = cheap / workflow brain |
| **Workflow** | Code picks the path; the model only does small jobs (intent, read, summarize). Anthropic / NVIDIA NAT |
| **Agent** (narrow) | The model picks tools itself (Google; our old 12B loop) |
| **Clipboard / notepad** | Session state we store (focus time, last hits, already tried, one-line notes). Not the video |
| **Intent** | Kind of question (talk / look / listen / …). Can be **several** at once |
| **Verb menu** | Closed list E4B may tick (`search_listen`, `open_eyes`, …). Code runs them |
| **Three speeds** | How Node runs the same form: ready-made job, many jobs at once, or a short hunt. See [19](19-three-speeds.md) |
| **Main / plan call** | Gemma reads last user messages + notepad and fills the form. Does not search the video |
| **Notepad clock** | Times like 1:04 live in SQLite, not in what the user typed |
