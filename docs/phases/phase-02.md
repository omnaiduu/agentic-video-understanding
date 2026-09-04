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

**FPS** — frames per second. Higher = more pictures, more cost. A 10-second window at 1 FPS is 10 pictures; at 10 FPS is 100.

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

## Proposed caps (from the tool doc)

These exist so the future brain cannot dump the whole movie.

| Rule | Proposed number | Why |
|---|---|---|
| Zoom window | max **8 seconds** if FPS is “high” | Look closely at a moment |
| Max FPS | **10** | Fast motion without exploding cost |
| Max pictures per call | **64** | Fits what Gemma can reasonably see |
| Long window (“skim”) | only if FPS is very low (**≤ 0.25**, i.e. one picture every 4s) **and** still ≤ 64 frames | Peek across a long span without 2h of images |
| Audio slice | max **30 seconds** | Gemma’s audio gulp is about that |
| Two-hour gulp | **always error** | `get_frames(0, 7200, fps=1)` must never run |

**If the caller exceeds a cap:** proposed **reject** with a clear error (“max 8s at this FPS”). Then the brain can retry smaller. Alternative: silently shrink the window. Reject is clearer.

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
