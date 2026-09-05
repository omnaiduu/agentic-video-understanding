# Phase 4 — Speech phone book

**Status:** not locked. Human answers the questions at the bottom first.

Depends on: [Phase 1](phase-01.md) (file), [Phase 3](phase-03.md) (JSON loop). Do not re-open those.

Product (short): after a file is stored, we **write down the words once**. Later, “what did she say about pricing?” can **find a time** without Gemma listening to two hours.

Related: [Whisper](../07-models-and-indexes.md) · [tools](../06-tools.md) · [phase map](../12-build-phases.md)

---

## What we are trying to do

Whisper listens to the whole file **once** (ingest). We save lines: *at 12:04 she said “pricing is $99”*.

When you ask a talk question, our state machine can **search that notebook** (text search). We hand Gemma the hits (times + snippets). She may then `look` at that time (Phase 2 frames) and `answer`.

Question 2 does **not** run Whisper again.

Whisper has **no eyes**. It will not describe a red light or a slide. That is Phase 5.

---

## This *is* RAG — the choice is the retriever

**RAG** = retrieve a few pieces, then the model answers from those pieces (and here, may `look`/`listen` to confirm). We are **not** “no RAG.” We are **not** stuffing the whole talk into Gemma.

The fight is only: **what do we retrieve, and with what engine?**

Speech is a waveform. “What did she **say**” is about **words**. To search words you almost always **transcribe first** (Whisper). After that, retrieval is over **text with timestamps**. That is “RAG over speech” in practice: audio → text+time → retrieve → Gemma.

Skipping Whisper and doing RAG on **raw audio vectors** finds *how it sounds* (clap, chirp). It does **not** reliably find the word “pricing.” That engine is CLAP, Phase 6, different question.

We are **not** training a new model. Options below are all off-the-shelf.

### Retriever options (pick one for Phase 4)

**A — Keyword / BM25 (SQLite FTS5)**  
Technical: SQLite’s built-in full-text tables. Tokenizer splits words, BM25 ranks lines that contain the query terms. We store `{start_s, end_s, text}` per Whisper **segment**. Query string from Gemma’s `search` JSON. Return top ~8 rows.

- Why it is strong: talk questions often use the **same words** (names, “pricing”, “NATO”, quotes). No extra model at query time. Lives in the same `app.db`. Matches the original architecture doc.
- Why it is weak: “how much does it cost?” may miss a line that only says “pricing.” Typos / ASR errors (“prising”) can miss.

**B — Dense RAG on the transcript**  
Technical: same Whisper segments. A **small text** embedder (e.g. E5 / MiniLM — not SigLIP, not a model we train) → one vector per segment → sqlite-vec or FAISS. Query: embed the question, nearest neighbors.

- Why: paraphrase and “cost” ≈ “pricing.”
- Why not required on day one: extra ingest GPU, extra index, still depends on Whisper quality. If ASR is wrong, vectors are wrong too.

**C — Hybrid**  
Run A and B, merge (e.g. RRF). Best quality, most code. Can be Phase 4b.

**D — RAG on raw audio only (no Whisper)**  
CLAP-style chunks. Right for “when did it clap.” Wrong as the **only** index for “what did she say.”

**E — Put the whole transcript in the prompt**  
A 2-hour talk is a long document. Can work for short videos; blows up for long ones; also tends to skip `look` (we already said don’t answer from the index alone). Not the spine.

**What I would ship first: A**, because Find is “get a time from words we already wrote down,” Understand stays Gemma on a short `look`. Add **B** later on the **same** `TranscriptLine` table if paraphrase fails. I will **not** lock A without you — you asked for the why, not a silent lock.

---

## Words

**Whisper** — speech → text + timestamps. We use **faster-whisper** (same model, faster engine).

**Ingest** — the one-time listen. Slow (minutes on a long file). Not part of the chat request.

**FTS** — “full text search” inside SQLite. Find “pricing” in the notebook in milliseconds.

**`search`** — a new move in our JSON form, next to `look` / `listen` / `answer`. **Not** a vLLM tool call. Our Python runs the search.

---

## How it will work

**After upload (Phase 1 still saves the file first)**

```
file saved, ffprobe done
→ status processing (speech)
→ faster-whisper on original.{ext}
→ rows in TranscriptLine
→ transcript_ready = true
```

HTTP upload does **not** wait for Whisper. Chat can already do “what’s at 0:10?” before the notebook exists. Talk-search only works when `transcript_ready`.

No audio stream → skip Whisper, `transcript_ready` false, `search` returns empty.

**Chat (Phase 3 loop, one extra action)**

JSON `do` is now:

- `look` — frames (already locked)
- `listen` — wav (already locked)
- `search` — `{ "query": "pricing" }` → our FTS → we put hits in the **next prompt as text** (times + quotes). No pictures in this step.
- `answer`

Example: “what did she say about pricing?” → `search` → hits at 12:04 → maybe `look` 12:03–12:08 → `answer`.

**Caps:** search returns a short list (e.g. top 8 hits). Not the whole transcript in one gulp.

---

## Locked from older docs (unless you change them)

- Engine: **faster-whisper** (not whisper.cpp unless you insist)
- Store **segments** (a sentence/chunk + time), not every word
- If Whisper fails: file stays, `transcript_error` set, chat still works for timed looks
- Same ingest function can later run on Modal; Phase 4 may run **in-process background** (demo)

---

## Plan (agent)

1. `TranscriptLine` table + SQLite FTS5
2. `video.transcript_status`: pending | processing | ready | error | skipped
3. Background ingest after Phase 1 save
4. `search_transcript(query)` Python function
5. Add `search` to the vLLM JSON schema + prompt
6. State machine: run search, append text hits, loop
7. Tests: tiny spoken fixture **or** inject fake lines and search “pricing” → a time. Do not require a GPU if we inject lines for unit tests; one optional Whisper test if ffmpeg can make a beep+tts… keep unit tests **without** downloading large Whisper weights if possible (mock the transcriber). One marked integration test if weights exist.

**Libraries:** `faster-whisper`. No SigLIP, no CLAP.

---

## Questions (lock these)

0. **Retriever:** **A** FTS5/BM25, **B** dense text embeddings on Whisper lines, **C** hybrid A+B, or **D** skip Whisper and audio-embed only (I would not pick D for “what did she say”)?  
1. **Whisper size:** turbo vs large-v3?  
2. Background ingest (don’t block upload)?  
3. `search` in the same JSON as look/listen/answer?

When these are answered, mark **LOCKED**.

## Done when

- After ingest, “pricing” finds a timestamp from stored text
- Second question does not run Whisper
- Timed “what’s at 0:10?” still works if transcript is not ready
- Gemma is not fed the whole talk
