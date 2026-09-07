# Phase 10 — Upload in the browser

**Status: LOCKED** (library file picker; byte progress; Query poll; jump to video page).

Depends on: [Phase 1](phase-01.md) (`POST /videos` multipart, 2 GB cap, status), [Phase 9](phase-09.md) (Start + shadcn + Query + library).

Product (short): pick a file in the website, watch it go **processing → ready** (or error), then open that video’s page.

Related: [phase map](../12-build-phases.md)

---

## What we are trying to do

On `/`: choose an mp4 (or allowed audio). Browser **POSTs** to FastAPI. Byte **progress**, then Query **polls** until `ready` or `error`. Then go to `/videos/:id`.

Same caps as Phase 1. Oversize → 413, shown as an error. Models stay on the backend. UI only waits.

---

## Locked

| Topic | Decision |
|---|---|
| Where | File picker **on the library** (`/`). No `/upload` route |
| File in | **Upload only** in the UI. Server path stays curl/API |
| Progress | **Byte %** during POST, then status while ingest |
| Poll | TanStack Query `refetchInterval` until `ready` / `error` |
| After ready | **Navigate to `/videos/:id`** |
| Types / size | Same as Phase 1 (mp4 + audio, 2 GB) |
| Write path | Browser → FastAPI. No Start server fn writing files |

---

## How it will work

```
Library (/)
  [Choose file] → POST /videos multipart
                → upload %
                → poll GET /videos/{id}
                → ready → go to /videos/{id}
                → error → show error_message
```

shadcn: Button, Progress. Mutation + list invalidate.

---

## Plan (agent)

1. File input + Progress on `/`
2. Multipart POST; API still enforces 2 GB
3. Poll until ready/error; then navigate
4. Tests: mock processing → ready; 413 visible; no 2 GB fixture

Implement only this file after 9.

## Done when

- Short mp4 in the UI becomes ready and the watch page opens
- Ingest / oversize errors are readable
- No player, no chat yet
