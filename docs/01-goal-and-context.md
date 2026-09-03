# Goal and context

## What this project is about

Google launched **agentic video understanding** in Gemini (3.7 / 3.6 / 3.5 Flash) on **1 September 2026**. The model does not ingest a video at a fixed 1 FPS. It gets a **pointer** (file id, duration), then **Think → Act → Observe**: search transcript, fetch a time window of frames at a chosen FPS, or fetch audio — only what it needs.

We are building the **open-weight equivalent**: same loop, our tools, our indexes.

This is **not** “ffmpeg + LLM” as a slogan. ffmpeg only cuts. The product is:

1. A **planner** (Gemma 4) that decides what to open
2. **Tools** that open slices
3. **Indexes** so those tools do not scan two hours with the big model
4. Optional **export** of a clip/audio file + URL for the user

## Why we are doing it

Static video into an LLM is expensive and still misses sub-second events (default 1 FPS). Google reports up to **88% fewer tokens**, **66% lower cost**, **~7% higher accuracy** with the agentic loop. Long lectures, CCTV, sports, and “needle in a haystack” questions need this pattern. We want the same behavior with models we can host (Modal) and open weights.

## What we realized (the hard lessons)

1. **The product is the agent (tools at question time).** Ingest indexes are a cache so tools are cheap — not a second product.
2. **Whisper has no eyes.** It cannot describe slides, red lights, or birds. Speech index ≠ scene diary.
3. **Gemma has no cheap 2-hour scan.** Gemma 4 video is about **60s at 1 FPS** per gulp; audio about **30s**. Long video **requires** tools (and usually indexes).
4. **One index cannot cover all questions.** Speech, pictures, and sounds are three channels. Image embeddings do not find a bird **chirp**. Transcript does not find a silent red light.
5. **`search_notes` (VLM captions at ingest) is not our plan.** We do not run a VLM while building the index. The VLM is **only the brain at question time**.
6. **CLIP-class models find; they do not answer.** Retrieval is a map. Gemma looks at real frames/audio and answers. Counting is done **in code** on hits, not by the LLM “remembering 847 claps.”
7. **Complexity came from mixing Google’s loop with extra RAG tricks.** Scene detect, pixel CLIP as the *story*, caption-every-3s, E2B-as-embedder — those were optional or wrong as the spine.

## Success looks like

- Upload or point at a long video
- Ask talk, visual, and sound questions
- Get timestamped answers grounded in a short rewatch
- Optionally get a **link to a cut clip or audio slice**
- Second question on the same file does **not** re-run Whisper/SigLIP/CLAP
