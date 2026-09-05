# Phase 6 — Sound phone book

**Status:** not locked. Human answers the questions at the bottom first.

Depends on: [Phase 1](phase-01.md) (file + Postgres), [Phase 2](phase-02.md) (ffmpeg audio), [Phase 3](phase-03.md) (JSON loop), [Phase 4](phase-04.md) / [Phase 5](phase-05.md) (pgvector already there).

Product (short): after a file is stored, we **index the sounds once**. Later, “when did the bird chirp?” can **find a time** without Gemma listening to two hours.

Related: [CLAP](../07-models-and-indexes.md) · [counting](../05-architecture.md) · [rejected](../04-what-we-rejected.md) · [phase map](../12-build-phases.md)

---

## Where we are

| Done on paper | This phase | Later |
|---|---|---|
| Hold file, scissors, Gemma JSON loop, **speech** notebook, **picture** notebook | **Sounds** notebook | Export (7), memory (8), website (9+) |

Whisper writes **words**. SigLIP sees **pictures**. Neither hears a chirp, a clap, or a beep. This phase is the ears for **non-speech sound**.

---

## What we are trying to do

Once per file we cut the audio into **short chunks** (a few seconds each). A small encoder (**CLAP / GLAP**) turns each chunk into a list of numbers. We save **numbers + time**.

When you ask a sound question, our state machine **searches those numbers**. We hand Gemma a few times as **text**. She may then `listen` to that slice and `answer`.

Question 2 does **not** re-encode the audio.

This **is** RAG for sounds. The encoder finds times; Gemma understands by listening. Search scores are **not** the answer.

**Counting** (“how many claps?”) is **Python** on the hits, not Gemma watching two hours and adding in her head. Nearby hits merge into one event. Stadium applause may be **one blob** — we say “applause 1:00–1:40”, not a fake 847.

---

## What this is not

- **Not** Whisper. Whisper is spoken words (Phase 4). “Clap” is often not a word in the transcript.
- **Not** SigLIP. Pictures do not hear.
- **Not** training an embedding model. We download a checkpoint and run it.
- **Not** hybrid keyword + dense. Raw audio has no words. (Spoken words are already searchable in Phase 4.)
- **Not** Gemma listening to the whole file. `listen` is still capped at 30 seconds.
- **Not** a clap-only detector. One search covers chirps, beeps, claps, gunshots ([04](../04-what-we-rejected.md)).
- **Not** dump-every-chunk into Gemma.

---

## Why we still need this after Whisper and SigLIP

| Question | Which book |
|---|---|
| “What did she say about pricing?” | Speech (Whisper text) |
| “Where is the red light?” | Pictures (SigLIP) |
| “When did the bird chirp?” | **This** (CLAP/GLAP) |

Same pattern as pictures: specialist encoder at ingest, Gemma only on a short slice.

---

## Words

**CLAP** — Contrastive Language-Audio Pretraining. Sounds → vectors, phrases → vectors. Same idea as SigLIP, for audio. **Search**, don’t narrate.

**GLAP** — newer (2025) CLAP-style model. Same job, same JSON action if we swap.

**Chunk** — a few seconds of audio we embed. Not the 30-second `listen` cap.

**Merge** — if hits sit next to each other, they are **one event**, not ten.

**`search_audio`** — a new move in our JSON form. **Not** a vLLM tool call. Our Python runs the search (and the count).

---

## How it will work

**After upload (Phase 1 still saves the file first)**

```
file saved, ffprobe done
       → background ffmpeg audio chunks
       → CLAP/GLAP each chunk → AudioChunk (start_s, end_s, embedding)
       → audio_status = ready
```

HTTP upload does **not** wait. No audio stream → skip, `audio_status = skipped`. Fail → file stays; timed `listen` still works if the file has audio.

**Chat (Phase 3 loop, one extra action)**

JSON `do` is now:

- `look` / `listen` / `search` / `search_visual` (locked)
- `search_audio` — `{ "query": "bird chirp" }` → nearest times → next prompt as **text** (`t` + score, plus merged count). No wav in this step.
- `answer`

Example: “when did the bird chirp?” → `search_audio` → hit at 0:41 → maybe `listen` 0:40–0:45 → `answer`.

**Count path (same phase, same search):**

```
search_audio → candidate times
            → merge nearby (gap in config, e.g. 1s)
            → count = len(clusters)   # Python, not Gemma
            → optional listen on 2–3 samples to verify
```

We put the cluster list and the count in the text we feed Gemma. She does not invent a total.

**Caps:** top ~8 raw hits (or the merged clusters). Not every chunk.

---

## Options (what I would pick)

| Topic | My pick | Other options | Why my pick |
|---|---|---|---|
| Encoder | **LAION-CLAP** (`laion/larger_clap_general` or `clap-htsat-fused`) | **GLAP** (`mispeech/GLAP`, 2025) | Sound events (chirp, clap, beep) are CLAP’s job. Speech **words** are already Whisper. CLAP is native in `transformers` (no `trust_remote_code`). GLAP is newer/multilingual — **same table, same JSON action**, name in config. |
| Chunk | **3 seconds**, hop **1.5s** (50% overlap) | 1s (more rows); 5s (miss short beeps); no overlap | Overlap so a 0.4s chirp is not split in half and lost. 3s is the middle of the 1–5s range in older docs. |
| Vectors | **Same Postgres / pgvector**, table `AudioChunk` | FAISS | Same as Phases 4–5. |
| What Gemma gets | **Times + merged count as text**, then she `listen`s | Attach wavs in the search step | Wavs would eat the 30s listen budget. Same pattern as speech/picture hits. |
| Counting | **Python merge + `len()`**, included in search results | Separate `count_events` JSON action; clap-only detector | Detector is too narrow. A second JSON verb can wait — the number is already in the search text. |
| JSON name | **`search_audio`** | overload `search` with a channel | Three phone books, three verbs. |

**Libraries:** `transformers` + LAION-CLAP (or GLAP via config), ffmpeg CLI, pgvector. No Whisper re-run. No SigLIP. No clap-only CNN.

---

## Plan (agent)

1. `AudioChunk`: video_id, start_s, end_s, embedding. Index on video_id + vector
2. `video.audio_status`: pending | processing | ready | error | skipped
3. Background ingest: ffmpeg chunks → CLAP → rows
4. `search_audio(query)`: embed phrase with **text** tower → KNN in this video → top hits → merge nearby → `{t, score}` + cluster count
5. Add `search_audio` to the vLLM JSON schema + prompt (tell the model to trust the Python count)
6. State machine: run search, append **text** hits, loop (Gemma may then `listen`)
7. Tests: inject fake vectors; `"beep"` finds the beep second; two nearby hits merge to count 1; mute file → skipped; mock CLAP in unit tests (no GPU)

Implement **only** this file after 1–5. No export. No website.

---

## Questions (lock these)

1. **Encoder — LAION-CLAP default, name in config (GLAP is a later swap).** OK?
2. **Chunks: 3 seconds, hop 1.5 seconds.** OK?
3. **Same Postgres / pgvector**, new table. OK?
4. **Counting in Python** (merge nearby + `len()`), included in `search_audio` text. No clap-only detector. OK?
5. **`search_audio` in the same JSON form.** Hits as **text times**, then Gemma `listen`s. OK?

When these are answered, mark **LOCKED**.

## Done when

- “When did the bird chirp?” can surface a timestamp from stored sound vectors
- Second question does not re-run CLAP
- “How many claps?” uses Python merge+count, not Gemma arithmetic
- Stadium blob is honest (one span), not a fake huge number
- Mute / no-audio files skip this index
- Timed listen still works if the sound book is not ready
- Gemma is not fed two hours of audio
