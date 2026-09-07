# Phase 9 — Website shell

**Status:** not locked. Human answers the questions at the bottom first.

Depends on: backend Phases [1](phase-01.md)–[8](phase-08.md) already serving HTTP (`GET /videos`, `GET /videos/{id}`, CORS open).

Product (short): a website exists with the **right screens**, talking to the API, even if upload and chat are still crude.

Related: [frontend plan](../08-frontend-backend.md) · [phase map](../12-build-phases.md)

---

## Where we are

| Done on paper | This phase | Later |
|---|---|---|
| Full backend loop (file → indexes → chat → export → follow-up) | **Pages + empty/loading/error** | Upload (10), watch+ask (11), clips/polish (12) |

Backend is locked. This is the first frontend slice. Same app, new folder. Not a second product.

---

## What we are trying to do

Open the site. See a **library** of videos (from `GET /videos`) or an **empty** state if there are none. Click a row → a **watch+ask page shell** (layout only). If the API is down → an **error** state, no crash.

Videos created with curl/API already show up. You do **not** need the upload form yet (Phase 10). You do **not** need a working player or chat yet (Phase 11).

---

## What this is not

- **Not** the upload picker (Phase 10).
- **Not** play + type a question + seek (Phase 11).
- **Not** clip download links or mobile polish (Phase 12).
- **Not** login, Next.js SSR, a design system, or a second backend.
- **Not** calling Gemma from the browser. The browser only talks to FastAPI.

---

## Words

**Shell** — real routes and states; inner widgets can be placeholders.

**Library** — list of videos + ingest status.

**Watch+ask** — the page where player and chat will live. This phase: title, status, empty panels.

**`VITE_API_URL`** — where the React app finds FastAPI.

---

## How it will work

```
web/  (Vite + React + TypeScript)
  /              library: GET /videos
                 empty | loading | error | list
  /videos/:id    shell: GET /videos/:id
                 missing id → error
```

Dev: Vite proxies `/api` to FastAPI **or** uses `VITE_API_URL` (CORS is already open). Same client either way.

Library rows: id, original name, duration, status. Click → watch+ask shell.

No player. No chat input. Placeholders with a one-line “coming in Phase 11” are fine.

---

## Options (what I would pick)

| Topic | My pick | Other options | Why my pick |
|---|---|---|---|
| App | **Vite + React + TypeScript** in `web/` | Next.js | We never needed SSR. SPA vs FastAPI is enough ([08](../08-frontend-backend.md)). |
| Routing | **react-router**: `/` and `/videos/:id` | Extra routes | Two screens. Keep it small. |
| Style | **CSS modules** (plain CSS per file) | Tailwind; one global.css | No design system. Modules avoid name clashes without a new toolchain. |
| API | Thin `fetch` wrapper + `VITE_API_URL` | axios, React Query | Two GETs. Don’t add a data library yet. |
| Auth | **None** | Login now | Backend has none. |
| List source | **`GET /videos`** (curl uploads count) | Fake in-memory list | Prove the UI is on the real API. |

**Libraries:** Vite, React, TypeScript, react-router. No Next, no Tailwind unless you pick it, no player SDK.

---

## Plan (agent)

1. `web/` Vite React TS app; README how to run next to the backend
2. API client: `GET /videos`, `GET /videos/:id`; timeout; readable errors
3. Routes: library + watch+ask shell
4. States: empty (no videos), loading, error (API down), list
5. Watch+ask: show metadata (name, duration, status); player/chat placeholders
6. Tests: render empty, render error on failed fetch, render a mocked list (no live Gemma)

Implement **only** this file after 1–8. No upload form. No `<video>`. No chat POST.

---

## Questions (lock these)

1. **Vite + React + TypeScript** in `web/`. Not Next.js. OK?
2. **CSS modules** (not Tailwind). OK?
3. Routes **`/` library** and **`/videos/:id` shell**. OK?
4. Library reads **`GET /videos`** (curl-uploaded files show up). API down → error, no crash. OK?

When these are answered, mark **LOCKED**. Next is the upload form (Phase 10).

## Done when

- Open `/` → empty or a list from the API
- Navigate to a video page shell
- API down → error state, app does not crash
- No upload, no player, no chat yet
