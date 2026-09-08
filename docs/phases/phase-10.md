# Phase 10 — Upload in the browser

**Status: LOCKED** (library file picker; byte progress; **live index status**; jump to video page while processing).

Depends on: [Phase 1](phase-01.md) (`POST /videos` multipart, 2 GB cap, status), [Phase 9](phase-09.md) (Start + shadcn + Query + library), ingest statuses from Phases [4](phase-04.md)–[6](phase-06.md) and [13](phase-13.md).

Product (short): pick a file, watch **upload %**, then watch **each phone book get built** (spinner + live lines), then the watch page is ready for chat in Phase 11.

Related: [phase map](../12-build-phases.md) · [how/hosting](../13-implementation-pass.md)

---

## What we are trying to do

On `/`: choose an mp4 (or allowed audio). Browser **POSTs** to FastAPI (byte **progress**). When the POST returns, go to `/videos/:id` **even if ingest is still running**. On that page: **spinner** + four lines that update as each index is built. Chat stays off until overall `ready`.

Same caps as Phase 1. Oversize → 413, shown as an error. Models stay on Modal (via FastAPI). UI only waits and shows status.

---

## Locked

| Topic | Decision |
|---|---|
| Where | File picker **on the library** (`/`). No `/upload` route |
| File in | **Upload only** in the UI. Server path stays curl/API |
| Upload progress | **Byte %** during POST |
| After POST | **Navigate to `/videos/:id` immediately** (do not wait for `ready`) |
| Ingest UI | **Spinner + four live lines** (speech, pictures, sounds, slides) |
| Poll | TanStack Query `refetchInterval` on `GET /videos/{id}` until overall `ready` / `error` |
| Chat | **Off** until overall `ready` |
| Types / size | Same as Phase 1 (mp4 + audio, 2 GB) |
| Write path | Browser → FastAPI. No Start server fn writing files |

---

## Live index panel (what you should see)

Not a silent “processing” badge. Four human lines, from the statuses the API already has:

| Line you see | API field |
|---|---|
| Speech index | `transcript_status` |
| Picture index | `visual_status` |
| Sound index | `audio_status` |
| Slide index | `slides_status` |

Each line: **waiting** · **building** (spinner) · **ready** · **skipped** · **error** (show `error_message` if that book failed).

Audio-only: pictures/slides show skipped. No-audio file: speech/sound skipped as the backend already decided.

---

## How it will work

```
Library (/)
  [Choose file] → POST /videos multipart
                → upload %
                → go to /videos/{id}   (may still be processing)
                → poll GET /videos/{id}
                → four lines update
                → overall ready → chat can turn on (Phase 11)
                → error → show error_message
```

shadcn: Button, Progress, (Spinner / Loader). Mutation + list invalidate.

---

## Plan (agent)

1. File input + byte Progress on `/`
2. Multipart POST; API still enforces 2 GB
3. Navigate to `/videos/:id` when POST returns (processing is OK)
4. Live four-line index panel + spinner; poll until ready/error
5. Tests: mock processing with books flipping pending → processing → ready; 413 visible; no 2 GB fixture

Implement only this file after 9.

## Done when

- Short mp4 in the UI uploads, then you **see each index get built**
- You are on the video page during ingest (chat still off)
- Ingest / oversize errors are readable
- No player, no chat yet
