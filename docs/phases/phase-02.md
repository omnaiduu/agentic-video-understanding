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

**FPS** — how many still pictures we take per second of video. 1 FPS = one photo each second. 8 FPS = eight photos each second (needed for fast motion).

---

## Caps in plain words

These are not four separate products. They are **one budget**: how much Gemma is allowed to *see* or *hear* in a single tool call.

Google’s Gemma 4 card ([source](https://ai.google.dev/gemma/docs/core/model_card_4)): roughly **60 seconds of video at 1 picture/sec**, and **30 seconds of audio**. We stay under that.

Think of a flashlight, not a floodlight:

| Number | Means | Example |
|---|---|---|
| **8 seconds** | Longest *close look* | “What happens at 1:04?” → open 1:03–1:11, not the whole talk |
| **10 FPS** | Densest sampling in that look | 8 seconds × 8 FPS ≈ 64 pictures. Fast action (sports) needs this. A lecture slide does not — 1 FPS is enough |
| **64 frames** | Hard max pictures **per call** | 8s × 8 FPS = 64. 60s × 1 FPS = 60. Both fit. `0→7200s at 1 FPS` = 7200 pictures → **blocked** |
| **30 seconds audio** | Hard max sound **per call** | Same as Gemma’s audio limit. Not “the whole podcast” |

**Skim (optional):** if we must peek across a *long* span, we take pictures rarely (e.g. one every 4 seconds) and still stop at 64 pictures. That is a blurry map, not a close look. Then we zoom.

The four numbers work as a set. Changing one without the others either wastes GPU or refuses useful zooms.

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

## Cap rules (same numbers as above)

- Close look: window ≤ **8s**, FPS ≤ **10**, and pictures ≤ **64**
- Skim: longer window only if FPS ≤ **0.25** and pictures still ≤ **64**
- Audio: ≤ **30s**
- Whole-file dump: always error

**If over the cap:** proposed **reject** with a clear error. Alternative: auto-shrink. Reject is clearer.

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

1. **Caps above OK?** 8s zoom, 10 FPS, 64 frames, 30s audio. Different numbers?

2. **Try it with curl?**  
   - **A** — only Python + tests (smaller).  
   - **B** — also HTTP, e.g. `POST /videos/{id}/frames` returns images, so you can demo scissors before Gemma exists.  
   I would do **B** if you want to *see* a cut without waiting for the brain; **A** if you want this slice tiny.

3. **Oversize:** reject with an error (recommended), or auto-shrink the window?

When these are answered, mark **LOCKED** and implement only this file.

## Done when

- Short `get_frames` returns JPEGs with timestamps
- Short `get_audio` returns wav
- Too-long request never runs ffmpeg on the whole file
- Audio-only: frames error, audio works
- Original file unchanged
- No chat, no UI
