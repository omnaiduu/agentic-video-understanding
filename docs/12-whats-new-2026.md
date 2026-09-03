# What’s new vs this design (Sep 2026)

Research note after re-reading our docs, Google’s 1 Sep 2026 agentic-video posts, and 2025–2026 papers/engineering blogs. **The product spine is not outdated.** Google just shipped the same Think → Act → Observe loop we copied. What *is* dated is some of the **phone books** (indexes) and **serving tricks**, especially for talks and slides.

This does **not** unlock rejected ideas (VLM captions at ingest, E2B-as-CLIP, scene-detect as the story). It is a shopping list of swaps that keep the same tools.

## Verdict in one screen

| Keep (still modern) | Upgrade (better default) | Add later if talks/slides/sports fail |
|---|---|---|
| Agent loop + pass-by-reference | **GLAP** as audio default, not LAION-CLAP | **ColQwen / ColPali** for slide pages |
| Indexes = cache; Gemma only at question time | **WhisperX** (VAD + word times) around faster-whisper | **PE Core** or clip-level video embeddings for motion |
| Answers from rewatch, not search scores | Word-level FTS, not 20s Whisper blobs | **SAM2 / SAM3Count** for object counting |
| Count in Python, not in the LLM | Skip near-duplicate lecture frames | Mixed **agentic + static** (Google’s two-clip pattern) |
| SigLIP 2 over 2021 CLIP | Prefix cache + parallel tools on Gemma | Qwen-VL as `get_frames` eyes only |
| sqlite + ffmpeg + Modal | NVDEC / batched ingest | Late-interaction index if ColPali lands |

**Do not chase:** Muon / SOAP / Shampoo. Those are **pretraining** optimizers (Kimi K2, GLM-5, NVIDIA Megatron blogs). We are not training a foundation model. Fine-tune CLAP later with AdamW.

---

## What Google actually launched (the “talks”)

Sources: [Introducing Agentic Video](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-agentic-video-in-gemini/) (Rohan Doshi, Mario Lučić, 1 Sep 2026); [Developer guide](https://aistudio.google.com/learn/agentic-video-understanding-with-gemini) (Patrick Loeber); [Gemini video docs](https://ai.google.dev/gemini-api/docs/video-understanding).

They did **not** ship a new video foundation model. Same Flash family (3.7 / 3.6 / 3.5 Flash-Lite), flag `processing: "agentic"`. Vendor numbers vs **their own static 1 FPS baseline**: up to **88% fewer tokens**, **66% lower cost**, **~7% higher accuracy**. “Up to” is a ceiling on long-form (lectures, matches, multi-hour); Google’s own side-by-sides on short queries were closer to **26–39%** token drop.

Loop they published:

1. **Pass-by-reference** — metadata + file id, not the movie.
2. **Think** — which channel, which times.
3. **Act** — transcript-first; temporal zoom + **adaptive FPS**; audio slice.
4. **Observe** — pay only for materialized slices; another round if needed.

Extra details our docs did not lock:

| Google detail | Why it matters for us |
|---|---|
| **Transcript-first** is an explicit policy, not a hint | Router prompt should prefer `search_transcript` for talk questions |
| Adaptive FPS (0.1 skim ↔ 5–10 zoom) | We already clamp this; keep it |
| **Mixed mode**: one long file `agentic`, one short clip `static` | “Find this 10s highlight in the 90-min talk” is a real product path |
| **Implicit / explicit context cache** across turns | Multi-turn should reuse KV, not re-send frames |
| Static still wins on **&lt; ~5 min** clips (tool overhead vs gulp) | Short uploads can skip indexes and `get_frames` the whole thing |
| Sub-second retrieval, anomaly **resample**, counting | Same jobs we listed; they still **rewatch**, they don’t RAG-answer |
| Coming: Gemini app + **Ask YouTube** | Confirms “watch page Q&A” as the consumer shape |

Academic cousins (VideoExplorer / VideoTemp-o3 / VideoARM / EGAgent, 2025–2026) all converge on the same idea: **don’t uniformly sample; localize then densely look**. Google productized it. We copy the **API loop**, not those full papers.

---

## Visual index — SigLIP 2 is fine; 1 FPS stills are the weak part

**SigLIP 2** ([arxiv:2502.14786](https://arxiv.org/abs/2502.14786), Feb 2025) is still a correct default vs 2021 CLIP: stronger, multilingual, Apache-2.0. We were right to reject OpenAI CLIP as the spine.

What 2025–2026 changed:

### 1. Meta Perception Encoder (PE Core) beat SigLIP 2

[PE Core](https://arxiv.org/abs/2504.13181) (Apr 2025, NeurIPS 2025; [code](https://github.com/facebookresearch/perception_models)): contrastive encoder that **outperforms SigLIP 2 on image** and **InternVideo2 on most video** tasks, still as a (mostly) frame-level CLIP. Our docs already list it as “optional later.” For **sports / CCTV / “flying bird”**, promote it to the first swap if SigLIP 2 retrieval is weak — same `search_visual` tool.

### 2. Frame-average is a poor video model

A 2026 [open retrieval bake-off](https://github.com/mixpeek/video-embedding-benchmark) (small, but directionally honest): **SigLIP 2 mean-pool of 8 frames** loses badly to native video embeddings (Twelve Labs Marengo, Gemini Embedding 2) and even to old **X-CLIP** (cross-frame attention). Takeaway: **1 photo/sec + cosine** finds “there is a bird,” not “the bird takes off.” Motion queries need either:

- clip-level embeddings (8–16 frames, PE / X-CLIP / LanguageBind-class), **or**
- find a coarse window with SigLIP, then `get_frames` at high FPS (what Google does).

We already do the second. The first is the cheap ingest upgrade if sports fail.

### 3. Talks are slides. SigLIP does not read “Pro $99”

This is the largest product gap. ColPali (ICLR 2025, [arxiv:2407.01449](https://arxiv.org/abs/2407.01449)) and **ColQwen2 / ColQwen2.5** embed **page screenshots** as ColBERT-style multi-vectors. They beat OCR → chunk → BGE pipelines on ViDoRe, including charts and tables. Engineering writeups: [Hugging Face](https://huggingface.co/blog/manu/colpali), [Vespa](https://blog.vespa.ai/retrieval-with-vision-language-models-colpali/), [Qdrant](https://qdrant.tech/documentation/tutorials-search-engineering/pdf-retrieval-at-scale/).

Our locked story: transcript (or visual) for **time** → `get_frames` → Gemma **reads**. That still works when the time is known. It fails when the user asks “which slide had the $99 price?” and nobody said “ninety-nine.” SigLIP finds “a slide,” not the number.

**Recommendation (not v1-blocking):** optional `search_slides` on **deduped** frames (one vector set per unique slide). Same Gemma rewatch. Do **not** OCR every frame at ingest — ColPali *replaces* that pipeline.

Near-duplicate **lecture** frames: perceptual hash or cosine-collapse consecutive SigLIP vectors. That is **not** PySceneDetect (cuts ≠ new slide). It is a cheap cache win we rejected scene-detect for the wrong reason if we never dedup at all.

---

## Speech index — Whisper family is the ecosystem; timestamps are the 2023 leftover

faster-whisper (large-v3 / turbo) is still the pragmatic multilingual default. What is dated is treating **segment-level Whisper times** as the search unit.

2026 ASR picture ([AssemblyAI roundup](https://www.assemblyai.com/blog/top-open-source-stt-options-for-voice-applications), [Presenc leaderboard](https://presenc.ai/research/best-open-weight-speech-to-text-models-2026), NVIDIA Canary-1B-v2 / Parakeet-TDT):

| Job | Better 2026 default |
|---|---|
| Multilingual talks | Whisper large-v3 **turbo** via faster-whisper (keep) |
| English batch throughput / WER | NVIDIA **Parakeet TDT** or **Canary** (swap behind same `search_transcript`) |
| **Word-level times** for “when did she say pricing?” | **WhisperX**: VAD → transcribe → wav2vec2 forced alignment ([m-bain/whisperX](https://github.com/m-bain/whisperX), Interspeech 2023; still the production pattern in 2026 guides) |
| Hallucinated silence / applause | **Silero / pyannote VAD** before ASR (WhisperX does this) |
| Panel / Q&A “who said it?” | Optional **pyannote** diarization (gated HF models; not v1) |

Vanilla Whisper timestamps drift hundreds of ms. For clip export and jump-to-word, that is the product. **FTS should index words/sentences with start/end**, not 15-second blobs.

Keep: Gemma audio is **not** the 2-hour transcriber.

---

## Sound index — default GLAP

[GLAP](https://arxiv.org/abs/2506.11350) (Xiaomi, 2025, [dasheng-glap](https://github.com/xiaomi-research/dasheng-glap)): one contrastive space for **sound + music + speech**, multilingual. Classic LAION-CLAP is English sound/music and weak on spoken content. GLAP’s point is the **Dasheng** audio encoder (general), not BEATs/CED (events only) or Whisper/WavLM (speech only).

Our docs already say “LAION-CLAP **or** GLAP.” **Pick GLAP as v1** unless install pain is real. Tool API unchanged.

---

## Counting and tracking — search+merge is right for claps; not for objects

Claps / beeps: threshold + merge + `len()` is still the honest design. Stadium applause is one blob.

Repeated **objects / actions** (Google’s “count shots,” CCTV people): 2025–2026 papers moved to **SAM2** tracking and **SAM3Count**-style open-vocab count (CVPR 2026 workshops). CLIP hits double-count the same bird. If counting sports/CCTV is a launch demo, add a **code** tool (`track_and_count`) on a short window after `search_visual`, not a Gemma running total.

---

## Brain / serving — Gemma 4 lock is fine; the loop is under-optimized

Locked: Gemma 4 12B Unified as planner + eyes + short ears. Still correct for **one** omni model with tools.

Modern around it (engineering, not a new brain):

| Technique | Why |
|---|---|
| **Prefix / KV cache** on `handle_id` | Google bills implicit cache; we should not re-prefill the system prompt + last frames every tool round |
| **Parallel tool calls** | `search_visual` + `search_transcript` in one step |
| **Speculative decoding** (vLLM / SGLang) | Agent turns are decode-heavy |
| **Constrained tool JSON** (xgrammar / outlines) | Stops garbage timestamps |
| **FP8 / AWQ** on 12B | Same GPU, more QPS |
| Optional **Qwen2.5-VL / Qwen3-VL** only on `get_frames` | Stronger OCR; no native audio — do not replace the brain |

Short-video bypass: if duration &lt; ~5 min, allow a static gulp (Google’s own advice) instead of forcing three indexes.

---

## “Optimization techniques” — what that word means here

People now say “optimizer” for three different things:

1. **Training** (Muon, SOAP, KL-Shampoo) — [Keller Jordan](https://kellerjordan.github.io/posts/muon/), [NVIDIA Megatron blog](https://developer.nvidia.com/blog/advancing-emerging-optimizers-for-accelerated-llm-training-with-nvidia-megatron/), DeepSpeed Muon. **Irrelevant until we pretrain.** Do not fine-tune Gemma with Muon for v1.
2. **Inference** (speculative decoding, prefix cache, quantization, NVDEC) — **this is our cost curve.** Bottleneck is Gemma+frames, as we already wrote.
3. **Retrieval** (HNSW, int8/binary vectors, Matryoshka, hybrid BM25+dense, late interaction) — **this is index quality.**

Ingest engineering that *is* 2026-cheap:

- ffmpeg **NVDEC** / PyAV for 1 FPS extract (CPU decode is the silent tax)
- Batch SigLIP/PE forwards
- Drop near-duplicate frames
- Hybrid transcript search: SQLite FTS5 (BM25) **then** optional embedding rerank — we already have FTS; use it as primary for talk queries

**Vector DB:** one video @ 1 FPS is ~3.6k vectors/hour. **sqlite-vec brute force is enough** (exact KNN; ANN still experimental as of 2026 writeups). FAISS/USearch/LanceDB when we have **many** videos. Don’t start Qdrant. If ColPali arrives, single-vector FAISS is the wrong shape — need MaxSim / multi-vector (Qdrant and Vespa have recipes; for v1, brute-force MaxSim on a few hundred unique slides is fine).

---

## Suggested change to the build order (still don’t skip to captions)

Keep [implementation plan](09-implementation-plan.md) steps 1–6. Fold these into existing steps, not a new product:

1. Skeleton — add **duration gate**: short file → static `get_frames`; long file → tools.
2. Speech — **WhisperX align** + FTS on sentences/words; VAD on.
3. Visual — SigLIP 2 + **consecutive-frame dedup**; store `slide_changed` boolean.
4. Audio — **GLAP** default.
5. Export — unchanged.
6. UI — seek to **word** timestamp.
7. Polish — prefix cache; parallel tools; optional ColQwen `search_slides`; optional PE Core; optional SAM2 count.

---

## What we should still refuse

Unchanged from [what we rejected](04-what-we-rejected.md): whole-video Gemma gulp as the product, VLM caption diary, answer-from-index-only, E2B embedder, scene-detect as the finder, OCR-all-frames, graph DB on day one.

New refuse: **rewriting the agent because of Muon**, **Twelve Labs / Gemini Embedding as the open-source spine** (APIs, not weights we host on Modal), **knowledge-graph ingest** (EGAgent et al.) until entity questions actually fail.

---

## Bottom line

Google’s talks confirm our architecture. The 2026 upgrades that bite **this** repo are: **word-aligned transcripts**, **GLAP**, **slide-aware visual search** (dedup + later ColQwen), **video-aware embeddings or PE Core** when motion retrieval fails, and **inference caches** so the tool loop is cheap. Everything else is either already locked correctly or research we already parked.
