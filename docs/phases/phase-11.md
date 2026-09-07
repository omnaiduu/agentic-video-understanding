# Phase 11 — Watch and ask

**Status: LOCKED** (Video.js; save `session_id`; click-to-seek; Working…; collapsed tool trace; no export buttons yet).

Depends on: [Phase 1](phase-01.md) (`GET /videos/{id}/file` + Range), [Phase 3](phase-03.md) / [Phase 8](phase-08.md) (`POST /videos/{id}/chat` + `session_id`), [Phase 9](phase-09.md) (watch page shell), [Phase 10](phase-10.md) (upload lands on this page).

Product (short): **play** the file, **type a question**, see the **answer**, click a **timestamp** to jump there.

Related: [frontend](../08-frontend-backend.md) · [phase map](../12-build-phases.md)

---

## What we are trying to do

On `/videos/:id`: Video.js plays `GET /videos/{id}/file`. You ask; POST chat with saved **`session_id`**. Wait for one JSON. Click a time → player seeks. Collapsed **details** show look/search/listen steps.

Audio-only: Video.js with audio (or audio-only tech). Chat still works. Still indexing → chat off.

---

## Locked (your picks)

| Topic | Decision |
|---|---|
| Player | **Video.js** (not native-only, not Media Chrome). Same FastAPI file URL + Range |
| Session | **Save `session_id`** on the page + **localStorage** per video |
| Times | **Clickable chips → seek** (`player.currentTime(t)`) |
| While waiting | Disable send. Show **Working…**. No SSE, no fake typing |
| Tool trace | **Collapsed “details”** (`steps`). Not hidden, not always open |
| Export links | **Hide until Phase 12** |

Do not copy the file into `web/public`. Browser still does not call Gemma.

---

## How it will work

```
/videos/$id
  Video.js  src = {API}/videos/{id}/file
  Chat:
    POST { message, session_id }
    answer text + time chips → seek
    <details> tool trace
```

TanStack Query mutation. shadcn Textarea, Button, Badge.

---

## Plan (agent)

1. Video.js on the watch page; `src` FastAPI file; audio-only still plays
2. Chat history, input, Working…, mutation
3. Persist `session_id` (memory + localStorage)
4. Citation chips → `player.currentTime(t)`
5. Collapsed details for `steps`; no `export_url` UI
6. Tests: mock chat with a time; seek called. No live Gemma

Implement only this file after 10.

## Done when

- Ask → see answer
- Click a time → player jumps
- Refresh keeps the same session on that video
- Trace is one click away
- No clip-download UI yet
