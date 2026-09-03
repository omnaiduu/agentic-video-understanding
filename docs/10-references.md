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
- [LAION CLAP](https://github.com/LAION-AI/CLAP) — older **audio** embedder; fallback if GLAP is painful.
- [GLAP (Xiaomi)](https://github.com/xiaomi-research/dasheng-glap) — 2025 general language–audio pretraining; **v1 audio default**.
- [Meta Perception Encoder (PE Core)](https://github.com/facebookresearch/perception_models) — stronger **video** retrieval swap; same `search_visual` slot.
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

Later papers in the same loop: [VideoExplorer](https://arxiv.org/html/2506.10821v4) (“thinking with video”), [VideoTemp-o3](https://arxiv.org/pdf/2602.07801), [VideoARM](https://openaccess.thecvf.com/content/CVPR2026/html/Yin_VideoARM_Agentic_Reasoning_over_Hierarchical_Memory_for_Long-Form_Video_Understanding_CVPR_2026_paper.html) (CVPR 2026). See [12-whats-new-2026.md](12-whats-new-2026.md).

## Speech pipeline (timestamps, not just WER)

- [WhisperX](https://github.com/m-bain/whisperX) — VAD + faster-whisper + wav2vec2 word alignment + optional pyannote diarization. How we use it: [13-whisperx.md](13-whisperx.md).
- [NVIDIA Canary-1B-v2 / Parakeet-TDT](https://arxiv.org/pdf/2509.14128) — English/multilingual ASR that beats Whisper-large-v3 on speed; same `search_transcript` slot.
- 2026 roundups: [AssemblyAI open STT](https://www.assemblyai.com/blog/top-open-source-stt-options-for-voice-applications), [Presenc open-weight ASR](https://presenc.ai/research/best-open-weight-speech-to-text-models-2026).

## Visual retrieval beyond SigLIP 2

- [Perception Encoder (PE Core)](https://arxiv.org/abs/2504.13181) — Meta, Apr 2025; beats SigLIP 2 on image, InternVideo2 on most video. [Code](https://github.com/facebookresearch/perception_models).
- [ColPali](https://arxiv.org/abs/2407.01449) / ColQwen — late-interaction **slide/page** search; [HF blog](https://huggingface.co/blog/manu/colpali); [Vespa](https://blog.vespa.ai/retrieval-with-vision-language-models-colpali/); [Qdrant scale notes](https://qdrant.tech/documentation/tutorials-search-engineering/pdf-retrieval-at-scale/).
- [Mixpeek video embedding bake-off](https://github.com/mixpeek/video-embedding-benchmark) — frame-average SigLIP 2 is a weak video model vs temporal / native video embeddings.

## Audio

- [GLAP](https://arxiv.org/abs/2506.11350) — default CLAP-class upgrade (sound + music + speech, multilingual). [dasheng-glap](https://github.com/xiaomi-research/dasheng-glap).

## Counting / tracking (code tools, not the LLM)

- [SAM 2](https://github.com/facebookresearch/sam2) — promptable video segmentation/tracking.
- SAM3Count (CVPR 2026 workshop) — open-vocab count on images/video; same idea as our “count in Python.”

## Serving / retrieval engineering (not training optimizers)

- Prefix KV cache, speculative decoding, constrained tool JSON — vLLM / SGLang; Google’s agentic video also uses **context caching** across turns.
- sqlite-vec is enough per video; ANN (USearch, LanceDB, FAISS) when the **library** is large. sqlite-vec GA is still exact KNN as of 2026 writeups.
- **Muon / SOAP** — LLM **pretraining** ([Keller Jordan](https://kellerjordan.github.io/posts/muon/), [NVIDIA Megatron](https://developer.nvidia.com/blog/advancing-emerging-optimizers-for-accelerated-llm-training-with-nvidia-megatron/)). Not a v1 work item.
