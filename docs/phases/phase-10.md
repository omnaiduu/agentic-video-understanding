# Phase 10 — Upload in the browser

**Status:** not locked. Human answers the questions at the bottom first.

Depends on: [Phase 1](phase-01.md) (`POST /videos` multipart, 2 GB cap, status), [Phase 9](phase-09.md) (Start + shadcn + Query + library).

Product (short): pick a file in the website, watch it go **processing → ready** (or error). Then it sits in the library.

Related: [phase map](../12-build-phases.md)

---

## Where we are

| Done on paper | This phase | Later |
|---|---|---|
| Backend + website shell (list/shell) | **Upload + ingest progress** | Player + chat (11), clips/phone (12) |

The hallway exists. This phase is the door.

---

## What we are trying to do

On the library page: choose an mp4 (or allowed audio). Browser **POSTs** the file to FastAPI. You see **bytes going up**, then **status polling** until `ready` or `error`. The new row appears in the list. Click it → the Phase 9 shell (still no player/chat).

Same caps as Phase 1: **2 GB**, types FastAPI already accepts. Oversize → the API’s 413, shown as an error. Do not silent-shrink.

Whisper / SigLIP / CLAP still run **in the backend** (background). The UI only **polls** `GET /videos/{id}` (and list). It does not run models.

---

## What this is not

- **Not** the player or chat (Phase 11).
- **Not** path-register (`{"path": "..."}`) in the UI unless we lock it. Curl/API still can.
- **Not** a third upload SaaS (S3 browser SDK). Multipart to FastAPI.
- **Not** Start server functions writing the file. Browser → FastAPI, same as Phase 1.

---

## Words

**Multipart** — the browser sends the file as form data (`POST /videos`). Same as Phase 1 upload.

**Poll** — ask `GET /videos/{id}` every few seconds until `ready` or `error`.

**Upload progress** — bytes sent / total (XHR or `fetch` + Readable if we have it; `XMLHttpRequest.upload.onprogress` is the boring reliable way).

---

## How it will work

```
Library (/)
  [Choose file]  → POST /videos (multipart)
                 → upload % 
                 → TanStack Query poll GET /videos/{id}
                      status processing → spinner / “indexing…”
                      status ready      → row in list, stop poll
                      status error      → show error_message
```

Query: `useMutation` for the POST; `refetchInterval` while status is `processing` (or `uploaded`). Invalidate the library list when done.

shadcn: Button, Input (or hidden file input), Progress. Keep it on `/` — no extra `/upload` route unless you ask.

---

## Options (what I would pick)

| Topic | My pick | Other options | Why my pick |
|---|---|---|---|
| Where | **Button on the library (`/`)** | New `/upload` route | You did not add `/upload` in Phase 9. |
| File in | **Upload only** in the UI | Also a “path on server” text box | Path is for curl/dev. A website user picks a file. |
| Progress | **Byte %** while POST, then **status text** while ingest | Status only | 2 GB needs a bar or it looks frozen. |
| Poll | **TanStack Query** `refetchInterval` ~2s until ready/error | Manual `setInterval` | Query is already locked. |
| Types | Same as Phase 1 (mp4 + audio ffprobe accepts) | Video-only in the UI | Backend already allows audio. |
| After success | Stay on `/`, new row visible | Jump to `/videos/:id` | Either works; staying proves the list. Jump is nicer. **I would jump.** |

---

## Plan (agent)

1. File input + shadcn Button/Progress on `/`
2. `POST /videos` multipart; 2 GB client check optional (API still enforces)
3. Mutation + poll Query until `ready` / `error`
4. Show `error_message` from Phase 1
5. Invalidate video list; navigate to `/videos/$id` (if we lock jump)
6. Tests: mock POST + status sequence processing → ready; 413 shown; no real 2 GB file

Implement **only** this file after 9. No `<video>`. No chat.

---

## Questions (lock these)

1. **Upload control on the library page** (no `/upload` route). OK?
2. **UI is file-picker only** (server path stays API/curl). OK?
3. **Byte progress, then poll status with TanStack Query.** OK?
4. **After ready, go to `/videos/:id`.** OK? (Alternative: stay on the list.)

When these are answered, mark **LOCKED**. Next is watch + ask (Phase 11).

## Done when

- Pick a short mp4 in the UI; status becomes ready; it appears in the library
- Ingest error is readable
- Oversize is rejected with a clear message
- No player, no chat yet
