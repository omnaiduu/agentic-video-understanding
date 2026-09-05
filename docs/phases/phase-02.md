# Phase 2 — Scissors

**Status: LOCKED.** An agent may implement **only** this file after Phase 1. Do not start Phase 3 from here.

Depends on: [Phase 1](phase-01.md). Next: [Phase 3](phase-03.md).

Related: [tools](../06-tools.md) · [architecture](../05-architecture.md) · [phase map](../12-build-phases.md)

---

## What this phase is

Cut a **small** piece of a file we already stored: a few photos, or a short sound. Refuse a huge cut. No chat. No Gemma. No website.

---

## Locked decisions

| Topic | Decision |
|---|---|
| Functions | `get_meta`, `get_frames`, `get_audio` in `backend/app/tools/` |
| Picture cap | At most **64 photos** per `get_frames` call |
| Sound cap | At most **30 seconds** per `get_audio` call |
| Oversize | **Reject** with a clear error. Do not silent-shrink. Do not run ffmpeg on the whole file. |
| How photos are spaced | Code’s job: 1/sec over a longer span, or several/sec over a few seconds, still ≤ 64 |
| ffmpeg | subprocess CLI |
| Frame format | JPEG |
| Audio format | 16 kHz mono wav |
| Temp files | Delete after the call |
| Audio-only files | `get_audio` works; `get_frames` errors |
| HTTP for scissors | **No extra routes.** Tests call the Python functions. Chat HTTP is Phase 3. |
| Tool call vs structured output | **Phase 3.** Scissors do not talk to Gemma. |

**Count before cut:** `seconds × photos_per_second` > 64 → refuse. Audio duration > 30s → refuse. Start/end invalid → refuse.

---

## Plan (agent)

1. `app/tools/`: meta, frames, audio, caps
2. ffmpeg via subprocess; temp dir; delete after
3. Tests: tiny mp4 + audio from Phase 1 helpers; short slice works; oversize never calls a 2h extract; audio-only frames fail
4. No torch, no Gemma client, no React

---

## Done when

- Short `get_frames` → JPEGs + timestamps
- Short `get_audio` → wav
- Too-big request → error, original file unchanged
- No `/chat`
