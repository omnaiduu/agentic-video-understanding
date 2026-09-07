# Phase 11 — Watch and ask

**Status:** not locked. Human answers the questions at the bottom first.

Depends on: [Phase 1](phase-01.md) (`GET /videos/{id}/file` + Range), [Phase 3](phase-03.md) / [Phase 8](phase-08.md) (`POST /videos/{id}/chat` + `session_id`), [Phase 9](phase-09.md) (watch page shell), [Phase 10](phase-10.md) (upload lands on this page).

Product (short): **play** the file, **type a question**, see the **answer**, click a **timestamp** to jump there.

Related: [frontend](../08-frontend-backend.md) · [phase map](../12-build-phases.md)

---

## Where we are

| Done on paper | This phase | Later |
|---|---|---|
| Backend loop + library + upload | **Player + chat + seek** | Clip links, phone layout (12) |

This is the human loop: watch and ask. Clip download buttons are Phase 12 even if the API already returns `export_url`.

---

## What we are trying to do

On `/videos/:id`:

- **Play** the stored file (`GET /videos/{id}/file`, Range so seek works).
- **Type** a question. POST chat with the **same `session_id`** so “that frame” works.
- **Wait** (loop can take tens of seconds). Then show the answer text.
- **Click a time** in the answer → `video.currentTime = t`.

Audio-only: `<audio>` instead of `<video>`. Chat still works.

If the file is still `processing`, chat is disabled with a short “still indexing…” (upload poll from Phase 10 may still be running).

---

## What this is not

- **Not** clip / audio download chips (Phase 12). Ignore `export_url` in the UI for now, or show it as plain text only if you prefer — **my pick: hide until 12**.
- **Not** a fancy player (video.js / Media Chrome). Native tags first.
- **Not** streaming tokens. The backend returns **one JSON** when the state machine finishes. The UI waits.
- **Not** calling Gemma from the browser.
- **Not** phone stacking (Phase 12). A simple side-by-side that may wrap is enough.

---

## Words

**Media URL** — `GET /videos/{id}/file`. That is the player `src`. Already locked in Phase 1 for this reason.

**Seek** — jump the playhead to a citation time.

**`session_id`** — keep it on this page so follow-ups hit the same thread (Phase 8).

**Waiting** — input disabled, “Working…” until POST returns. No fake token stream.

---

## How it will work

```
/videos/$id
  <video src="{API}/videos/{id}/file" controls>   // or <audio>
  Chat:
    history (user / assistant text)
    input → POST /videos/{id}/chat { message, session_id }
         → show answer
         → render times as buttons → seek
```

TanStack Query: `useMutation` for chat. Keep messages in page state (and the session id). `session_id` from the first response; send it on every later POST. Persist in `localStorage` keyed by video id so refresh does not start a new thread (unless you say no).

shadcn: Textarea, Button, Badge (timestamps). Optional collapsed “details” for `steps` / tool trace.

---

## Options (what I would pick)

| Topic | My pick | Other options | Why my pick |
|---|---|---|---|
| Player | Native **`<video>` / `<audio>`** | video.js, Media Chrome | Phase 1 already streams with Range. Extra player SDK is polish. |
| Media | **`GET /videos/{id}/file`** | Copy to public folder | Same origin or `API_URL`; CORS/Range already planned. |
| Session | **Keep `session_id` in the page + localStorage per video** | New session every load | “That frame” should survive refresh on the same file. |
| Times | **Clickable chips → seek** | Times as plain text | This is the product: jump to the moment. |
| While waiting | **Disable send, show Working…** | SSE / token stream | Backend is one JSON at the end. Streaming is a new API. |
| Tool trace | **Collapsed “details”** | Hide completely | Useful when the loop looks stuck. Not the main UI. |
| Export links | **Hide until Phase 12** | Render now | Phase 12 is that job. |

---

## Plan (agent)

1. Wire `src` to `{API}/videos/{id}/file` (Range). Audio-only → `<audio>`
2. Chat panel: history, input, mutation, waiting state
3. Send `session_id`; store it (memory + localStorage)
4. Parse `times` / citations → buttons → `currentTime = t`
5. Disable chat while `processing`; collapsed details for `steps`
6. Tests: mock chat JSON with a time; click seek (jsdom or component test). No live Gemma

Implement **only** this file after 10. No clip download UI. No new backend verbs.

---

## Questions (lock these)

1. **Native `<video>` / `<audio>`**, `src` = `GET /videos/{id}/file`. OK?
2. **Keep `session_id`** on the page and in localStorage for that video. OK?
3. **Timestamp chips seek** the player. OK?
4. **Wait for the full JSON** (no SSE). Collapsed tool-trace details. Hide export links until Phase 12. OK?

When these are answered, mark **LOCKED**. Last phase is clips + phone polish.

## Done when

- Ask a question on a ready video; see answer text
- Click a time; player jumps there
- Follow-up on the same page uses the same session
- Audio-only still chats
- No clip-download UI yet
