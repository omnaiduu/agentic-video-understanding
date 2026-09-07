# Phase 12 — Clips and polish

**Status: LOCKED** (clip **in the scrollable chat**; phone stack; delete button; root README). UI complete. **Phase 13** still adds the slide book.

Depends on: [Phase 7](phase-07.md) (`export_url`, `GET /videos/{id}/exports/{id}`), [Phase 11](phase-11.md) (watch + ask). Same TanStack Start + shadcn app.

Product (short): show **clip/audio in the conversation**, make the page work on a **phone**, make errors **readable**, write how to run the app.

Related: [phase map](../12-build-phases.md) · [rejected](../04-what-we-rejected.md)

---

## What we are trying to do

When chat includes an `export_url`, it appears **in that assistant message**, like the rest of the thread — not a separate pane. The chat is **scrollable**; older messages (text, times, clips) stay above. You can play the short cut there and **Download** it.

On a **phone**: main Video.js player **above**, chat **below**.

Delete: confirm on the watch page → `DELETE /videos/{id}` → library.

README at repo root: FastAPI + `web/`.

---

## Locked (your picks)

| Topic | Decision |
|---|---|
| Clip UI | **Inside the chat bubble** of that turn: small player + Download. Same scrollable conversation as before |
| Phone | **Stack** player above chat under ~768px (`md:`) |
| Delete | **Watch page button**, confirm, then API DELETE, back to `/` |
| README | **Root README**: Postgres, FastAPI, `web/`, env vars |
| Not | Login, signed URLs, crop/OCR, `search_notes`, scene detect, E2B embedder, Elasticsearch |

The big Video.js (Phase 11) stays the **source file**. The in-chat player is only the **exported slice**.

---

## How it will work

```
Chat (overflow-y: auto)
  user: …
  assistant: answer + time chips
  assistant: [mini player of export] [Download]
  …scroll keeps history

Width < ~768px
  source player
  chat under it
```

---

## Plan (agent)

1. If `export_url` on an answer, render mini `<video>`/`<audio>` + Download **in that message**
2. Chat column scrolls; don’t dump the clip outside the thread
3. Responsive stack
4. Readable copy: empty, ingest error, API/Gemma down, export-too-long
5. Delete with confirm
6. Root README: how to run both processes
7. No new ML. No login.

Implement only this file after 11.

## Done when (UI complete)

From the **website**, a long video can: (a) speech question, (b) silent visual, (c) sound question, (d) follow-up without re-ingest, (e) clip **in the chat**, (f) usable on a phone — without loading the whole file into Gemma.

Slide-text search (“which slide had **Pro $99**?”) is **Phase 13**.
