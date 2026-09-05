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

1. **Whisper size:** **turbo** (faster ingest, a bit sloppier) or **large-v3** (better text, slower)? I would use **turbo** for the demo, same code path to swap the name later.
2. **Upload waits?** I would **not** wait. Return the video id immediately; speech index fills in the background. OK?
3. **`search` in the same JSON form** as look/listen/answer — OK? (Not vLLM `tools=`.)

When these are answered, mark **LOCKED**.

## Done when

- After ingest, “pricing” finds a timestamp from stored text
- Second question does not run Whisper
- Timed “what’s at 0:10?” still works if transcript is not ready
- Gemma is not fed the whole talk
