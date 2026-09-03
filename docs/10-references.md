# References

## Google — agentic video

- [Introducing Agentic Video in Gemini](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-agentic-video-in-gemini/) — 1 Sep 2026. Rohan Doshi, Mario Lučić. 88% tokens, 66% cost, ~7% accuracy. `processing: "agentic"`.
- [Agentic video understanding — developer guide](https://aistudio.google.com/learn/agentic-video-understanding-with-gemini) — Patrick Loeber. Think → Act → Observe; pass-by-reference; transcript / adaptive FPS / audio.
- [Gemini Enterprise Agent Platform — video understanding](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/capabilities/video-understanding) — `media_processing=AGENTIC`; `step_list` on follow-ups.
- [Gemini API video understanding](https://ai.google.dev/gemini-api/docs/video-understanding) — static 1 FPS baseline, tokenization.

## Google — agentic vision (stills)

- [Introducing Agentic Vision in Gemini 3 Flash](https://blog.google/innovation-and-ai/technology/developers-tools/agentic-vision-gemini-3-flash/) — 27 Jan 2026. Crop/zoom/code on **one image**. Different from video timeline tools.

## Models we chose or compared

- [Gemma 4 model card](https://ai.google.dev/gemma/docs/core/model_card_4) — E2B/E4B/**12B Unified** = text+image+audio; 31B/26B-A4B no audio; ~60s video / ~30s audio limits.
- [Gemma 4 12B unified architecture](https://blog.google/innovation-and-ai/technology/developers-tools/introducing-gemma-4-12b/)
- [SigLIP 2](https://arxiv.org/abs/2502.14786) — default **visual** embedder.
- [LAION CLAP](https://github.com/LAION-AI/CLAP) — default **audio** embedder family.
- [GLAP (Xiaomi)](https://github.com/xiaomi-research/dasheng-glap) — 2025 general language–audio pretraining; upgrade path.
- [Meta Perception Encoder (PE Core)](https://github.com/facebookresearch/perception_models) — optional stronger **video** retrieval later.
- faster-whisper / OpenAI Whisper — speech index.

## Related (not v1 spine)

- Omni-Embed-Audio (ACL 2026) — LLM as audio retriever; why E2B-embed is **research**, not v1.
- FineLAP, M2D-CLAP, WavLink — stronger CLAP-class models; same `search_audio` slot.

## Infra

- [Modal pricing](https://modal.com/pricing) — GPU per-second (L4 / A10 / …).
- ffmpeg — extract and export.
- FastAPI, sqlite-vec / FAISS.

## Academic agentic video (background only)

VideoAgent, Video-RAG, DrVideo, EGAgent — iterative frame finders. Closer in *spirit* than in API. We copy **Gemini’s tool loop**, not those full products.
