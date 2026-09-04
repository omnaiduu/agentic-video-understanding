# Phase 2 — Scissors

**Status:** not locked. Human answers the questions at the bottom first.

Depends on: [Phase 1](phase-01.md) (a stored file with an id). Do not re-open Phase 1.

Product (short): the finished app’s brain will **look at a few seconds**, not the whole tape. This phase builds the **scissors** that cut those seconds. There is still **no brain**. No chat. No website.

Related: [tools](../06-tools.md) · [architecture](../05-architecture.md) · [phase map](../12-build-phases.md)

---

## What we are trying to do

Take a video (or audio) we already stored. Cut a **short** piece:

- **Pictures:** a few JPEGs from a time range (`get_frames`)
- **Sound:** a short wav slice (`get_audio`)
- **Facts we already have:** duration, fps, kind (`get_meta`)

If someone asks for two hours of frames, we **say no**.

That is the whole phase. Gemma is not here yet. We still write the **real** functions she will call later, with the **real** caps.

## Why

A 2-hour file is thousands of pictures. The model cannot swallow that. Google’s idea: jump to a time, look at a short window. ffmpeg does the jump. These three functions **are** that jump.

We build them now so Phase 3 (brain) only has to *call* them, not invent them.

## Words

**ffmpeg** — the program that actually cuts. “Give me frames from 0:10 to 0:12 at 4 pictures per second.”

**Tool** — a Python function the brain will be allowed to call. In this phase humans/tests call them. Later Gemma calls the same functions.

**Cap** — a hard max we enforce in code. The caller does not get to ask for 7200 seconds at 1 FPS.

**One look** — one call to `get_frames` or `get_audio`. Like opening a book to one page, not reading the whole book.

---

## The cap (one rule)

A 2-hour video is like a photo album with thousands of pages. The AI cannot look at every page at once. So **each look is small**.

**The only rule that matters:**

- Pictures: at most **about 64 photos** in one look  
- Sound: at most **30 seconds** in one listen  

If someone asks for more, we **refuse**. We do not extract 7,000 photos from two hours.

That is the cap. Everything else is just *how* we pick those 64 photos:

- Slow talk / a slide: take **1 photo per second** for up to ~60 seconds (60 photos).  
- Fast action: take **several photos per second**, so the clip must be **shorter** (e.g. 8 seconds × 8 photos/sec ≈ 64 photos).  

Same pile of 64 photos. Either a longer stretch with few photos, or a short stretch with many photos. Never both (long **and** dense) — that blows past 64.

30 seconds of sound is the same idea: Gemma can only hear a short clip at a time.

We did not invent 64 and 30. They match what Gemma 4 can swallow (about a minute of video at 1 photo/sec, 30 seconds of audio).

**Phase 2 does not talk to Gemma.** We only cut files and enforce this rule. How Gemma *asks* for a cut (tool call vs JSON / structured output) is **Phase 3**. Either way our code runs ffmpeg. It does not change this phase.

---

## How Gemma actually sees a cut (checked)

Gemma 4 **12B Unified** takes **text + images + audio** in a prompt. It also has **function calling** (it outputs “call `get_frames` with these times”).

Official function-calling docs show tool **results as text/JSON** (weather, etc.) — not as a special “image tool-result” type ([function calling](https://ai.google.dev/gemma/docs/capabilities/text/function-calling-gemma4)).

So we do this (our runtime, Phase 3):

1. Gemma: `get_frames(1:03, 1:11, fps=8)`
2. **Our code** runs ffmpeg, gets JPEG bytes
3. We send a **new multimodal turn**: text (“frames at 1:03, 1:03.125, …”) **plus the actual images** (and/or a wav for `get_audio`)
4. Gemma looks at those images/audio and answers or calls another tool

That is multimodal. The scissors return **bytes**. The brain loop **attaches** those bytes as image/audio parts. We do not base64-dump 64 JPEGs into a JSON string and hope she “sees” them.

Audio: 16 kHz wav matches how Gemma 12B ingests audio (raw-ish waveform / 16 kHz family). Cap 30s matches the card.

Phase 2 only produces the bytes. Phase 3 wires them into the Gemma request.

---

## Why only these three functions *in this phase*

The **finished** app has more tools ([06](../06-tools.md)):

| Tool | When |
|---|---|
| `get_meta` / `get_frames` / `get_audio` | **Phase 2** — scissors |
| `search_transcript` | Phase 4 — needs Whisper |
| `search_visual` | Phase 5 — needs SigLIP |
| `search_audio` | Phase 6 — needs CLAP |
| `export_clip` / `export_audio` | Phase 7 — file for the *user*, not for Gemma’s eyes |
| `crop_frame` / `ocr_frame` | Later, only if tiny objects / slides fail |

Phase 2 is not “the whole toolbox.” Search needs indexes. Export is a download, not a look. Extra tools without those pieces would be empty stubs.

---

## How it will work

Python functions (not a second product):

```
get_meta(video_id)
  → {duration_s, fps, has_video, has_audio, kind}

get_frames(video_id, start_s, end_s, fps)
  → [{t, jpeg_bytes}, …]   # each picture tagged with its time

get_audio(video_id, start_s, end_s)
  → wav bytes
```

Under the hood:

```
ffmpeg -ss START -i original.mp4 -t DURATION -vf fps=FPS  frame-%03d.jpg
ffmpeg -ss START -i original    -t DURATION -vn -ac 1 -ar 16000 slice.wav
```

Work in a temp folder, return bytes, **delete temp files**. Do not fill the disk.

**Audio-only files** (Phase 1 allowed them): `get_audio` works. `get_frames` returns a clear error (no pictures).

**Video files:** `get_audio` pulls the soundtrack for that window.

**Out of range** (start after the end of the file, end before start): error.

## How we enforce it in code

Count photos that *would* come out: `seconds × photos_per_second`. If that is over 64, refuse. If audio longer than 30 seconds, refuse. Never run ffmpeg on the whole file.

Defaults for a close look (not a separate product): a few seconds, a few photos per second, still under 64. A slow scan can be longer if photos stay under 64.

If over: **reject**. Do not silently shrink.

## What we will not build here

- Gemma / `/chat`
- Whisper / search
- `export_clip` (that writes a file + URL for the user — later)
- Website
- Saving extracted frames forever

---

## Plan (agent)

1. `backend/app/tools/` : `get_meta`, `get_frames`, `get_audio`
2. Shared cap checks **before** ffmpeg
3. ffmpeg via **subprocess CLI** (not MediaBunny, not Node)
4. JPEG frames, **16 kHz mono wav** audio (Whisper/Gemma-friendly later)
5. Tests on Phase 1’s tiny mp4 + audio: short slice works; oversize fails; audio-only `get_frames` fails
6. No new ML libraries

Optional HTTP to try scissors without Python (see question 2).

**Layout add**

```
backend/app/tools/
  __init__.py
  caps.py
  meta.py
  frames.py
  audio.py
backend/tests/test_tools.py
```

---

## I would pick (unless you say no)

- subprocess ffmpeg CLI
- JPEG, not PNG (smaller)
- 16 kHz mono wav
- Reject oversize; do not silent-clamp
- Temp files deleted after each call
- Tools are Python functions first (what Gemma will call)

---

## Questions (answer these to lock)

1. **The rule:** at most ~64 photos per look, at most 30 seconds of sound. If someone asks for more, we **say no**. OK?
2. **Can you try a cut before Gemma exists?** Tests only, or also an HTTP route you can curl?
3. Tool call vs structured output: **not this phase.** We pick that in Phase 3. OK to leave it?

When these are answered, mark **LOCKED** and implement only this file.

## Done when

- Short `get_frames` returns JPEGs with timestamps
- Short `get_audio` returns wav
- Too-long request never runs ffmpeg on the whole file
- Audio-only: frames error, audio works
- Original file unchanged
- No chat, no UI
