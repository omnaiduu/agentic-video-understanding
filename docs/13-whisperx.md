# WhisperX — the speech phone book

Plain-language note: **what it is, why we use it, what questions it unlocks, how the pieces work, how to build it.** Code is not in this repo yet. This is the speech half of ingest (step 2 in the [implementation plan](09-implementation-plan.md)).

Google’s agentic video is **transcript-first** for talk questions. Our transcript must be searchable **and** jump to the right second. That is WhisperX’s job. It has **no eyes** (slides, red lights) and **no ears for claps** (that is GLAP). Speech only.

---

## Why not plain Whisper?

Whisper (via **faster-whisper**) is good at **what was said**. Its **clock is sloppy**. It often stamps a whole chunk (many seconds) as one block.

**Example.** At **41:12** she says “Our **pricing** starts at ninety-nine.”

Plain Whisper may store:

> **41:08–41:22** — “so to recap the roadmap our pricing starts at ninety-nine…”

Search for “pricing” jumps to **41:08**. The user hears four extra seconds of “roadmap.” `export_clip` starts too early.

For this product that is a bug: timestamps, seek-in-player, and cut clips all need **this word → this second**.

---

## What WhisperX is (not one model)

WhisperX is a **factory** that runs specialists in order. We run it **once per video** at ingest, save the result, reuse it on every question.

```
audio
  → 1. VAD          is anyone talking?
  → 2. Whisper      what words?          (faster-whisper)
  → 3. Aligner      when was each word?  (wav2vec2)
  → 4. Diarization  who?                 (pyannote)  — **ON** for this demo (Speaker 1/2); drop if it blows ~$30/mo
         ↓
  SQLite / session: word + start + end  (+ speaker)
         ↓
  search_transcript  →  jump / clip at that time
```

| Piece | Everyday name | What it answers |
|---|---|---|
| **VAD** | Silence cutter | Speech vs quiet / applause |
| **Whisper** | Typist | The words |
| **Aligner** | Karaoke clock | Exact time of each word |
| **Diarization** | Voice splitter | Speaker 0 vs 1 — **not names** |
| **Parakeet / Canary** | Another typist | Same job as Whisper, often faster English — **not** WhisperX |

**Parakeet is not WhisperX.** It does not do alignment or “who spoke.” Later we can swap the typist and keep the rest.

---

## Why we use it in *this* product

1. Google: search **transcript first**, then maybe open frames. Bad times → bad jumps → Gemma looks at the wrong window.
2. **Talks** are a first-class use case (“what did she say about pricing?”).
3. **Export** must start on the right syllable, not four seconds early.
4. Open-source **bundle**: VAD + fast Whisper + word clock + optional who. Nothing famous replaced that whole sandwich in 2026. Better *typists* exist (Parakeet); the **glue** is still WhisperX.
5. Once per file. Question 2 does not re-run it.

---

## Questions it helps (and what it cannot)

`search_transcript` after WhisperX. Gemma may still `get_frames` to read a slide.

| User asks | WhisperX enough to **find the time**? | Notes |
|---|---|---|
| “When did she say **pricing**?” | **Yes** — jump to the word | This is the whole point |
| “What did she say about pricing?” | **Yes** — retrieve nearby sentences | Gemma can quote; optional rewatch |
| “Give me the clip where she announced the price” | **Yes** — clip in/out from word times | Cap duration as usual |
| “Jump to ninety-nine dollars” if she **said** it | **Yes** if Whisper heard the words | Align fails on some numbers/symbols |
| “Who asked the price?” (panel) | Only if **diarization on** | v1 single-speaker: skip |
| “Which slide showed **Pro $99**?” (nobody said it) | **No** | Eyes: SigLIP / ColQwen + `get_frames` |
| “When did people **clap**?” | **No** | Sound book (GLAP), not speech |
| “When did the **red light** appear?” | **No** | Picture book |

If Whisper **misheard** a word, the aligner still times that **wrong** word perfectly. Clock ≠ spellcheck. Gemma rewatch still matters for the answer.

---

## How the stations work

### 1. VAD — “is this talking?”

Marks speech vs not-speech. Whisper only sees the talking boxes.

**Example.** 20 seconds of applause. Plain Whisper may invent “thank you, thank you.” That fake line lands in search. VAD: skip applause, don’t transcribe it.

### 2. Whisper — “what words?”

faster-whisper writes the script. Good multilingual default. Still chunky times — we do not trust those for seek/export.

### 3. Aligner — “when was each word?”

Does **not** rewrite the transcript. Fits **known** words onto the waveform (**forced alignment**).

1. Split a word into phonemes (tiny mouth-sounds): `pricing` → `P R AY S IH NG`. Order is locked.
2. Cut audio into ~10–20 ms frames (a film strip of the sound).
3. A **wav2vec2** model scores each frame: “does this slice sound like `P`? like `R`?”
4. Find one **legal path** through that grid (time going forward, phonemes in order, each phoneme lasting several frames). That search is **dynamic time warping** — karaoke: slide the lyrics until they match the singer.
5. First phoneme start → last phoneme end = **word** start/end.

**Example after align:**

| Word | Time |
|---|---|
| our | 41:11.4 |
| **pricing** | **41:12.1** |
| starts | 41:12.6 |
| ninety-nine | 41:13.2 |

Search “pricing” → **41:12.1**, not 41:08.

**Breaks on:** languages with no phoneme model (times fall back to chunks); some numbers/punctuation; two people talking over each other.

### 4. Diarization — “which voice?” (optional, off for v1 talks)

**pyannote.** Never reads the text. Never knows “Jane.” Only **SPEAKER_00** vs **SPEAKER_01**.

1. Fingerprint short chunks of voice (“what does this person sound like?”).
2. Cluster similar fingerprints = same speaker.
3. Stitch into **time boxes**: 0:00–12:03 voice A, 12:03–12:40 voice B.
4. **Glue:** each **aligned word** has a timestamp; drop it into whichever box contains that time.

```
12:01  SPEAKER_00  What's the price?
12:04  SPEAKER_01  Pricing starts at ninety-nine
```

Rename speakers in the UI later. Needs a Hugging Face token (gated models). Fails on overlap and similar voices. **One-person keynote: leave off.**

---

## v1 plan vs later

### v1 (single speaker talks — ship this)

At ingest:

1. ffmpeg extract audio.
2. WhisperX: **VAD + Whisper + align + diarization** (Speaker 1/2). English only. Drop diarization if Modal cost blows ~$30/mo.
3. Store for the session: `video_id, word, start_ms, end_ms, sentence_id, speaker`.
4. `search_transcript(query)` → FTS / word match → `{t, text, score}`.
5. Player seek and `export_clip` use **word** (or sentence) `start_ms`.

Prove: ≥10 min lecture, “when did she say X?” lands on the right second, not a 15s blob.

### Later (same `search_transcript` tool)

| If | Then |
|---|---|
| English bulk, need speed/WER | Swap typist to **Parakeet / Canary**; keep an aligner |
| Panels / interviews | Turn **diarization** on; store `speaker` |
| Align model missing for a language | Transcript still works; times stay chunky |

Do **not** run WhisperX on every chat message. Do **not** use Gemma to transcribe 2 hours.

---

## Is it “state of the art”?

**As an open bundle** (words + word clock + optional who): still what people ship in 2026. Inner pieces move:

- Better **typist:** NVIDIA Parakeet / Canary (English).
- **Who:** still mostly pyannote.
- Paid APIs (Deepgram, AssemblyAI) bundle the same jobs; we self-host on Modal.

We pick WhisperX for v1 because it is one pipeline, MIT-ish Whisper core, and it fixes the clock. We do not pick it because every inner model will stay #1 forever.

---

## What this is not

- Not a scene diary (no slides, no birds).
- Not clap/chirp search.
- Not the brain (Gemma still **verifies** on frames when needed).
- Not required to train anything.

See also: [models and indexes](07-models-and-indexes.md), [what’s new 2026](12-whats-new-2026.md), [WhisperX repo](https://github.com/m-bain/whisperX).
