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

You open the site in a browser (later: `cd web && npm run dev`).

**Library (`/`)**

- Loading: “Loading videos…”
- Empty: “No videos yet” (nothing in Postgres)
- Error: “Can’t reach the API” (backend off)
- List: each row shows name, duration, status (`ready` / `processing` / `error`). Click a row.

**Watch+ask (`/videos/:id`)**

- Loading, then title + duration + status
- Two empty boxes: “Player (Phase 11)” and “Chat (Phase 11)”
- Bad id or API down → error, with a link back to `/`

Videos you already created with curl show up. You do **not** upload from the browser yet. You do **not** play or ask yet.

This is the hallway. Phase 10 puts a door (upload). Phase 11 puts the furniture (player + chat). Phase 12 paints it (clips, phone layout).

---

## What this is not

- **Not** the upload picker (Phase 10).
- **Not** play + type a question + seek (Phase 11).
- **Not** clip download links or mobile polish (Phase 12).
- **Not** login, Next.js SSR, a design system, or a second backend.
- **Not** calling Gemma from the browser. The browser only talks to FastAPI.

---

## Words

**Shell** — the rooms of the house with the lights on. You can walk into Library and Watch. The furniture (upload, player, chat) comes in later phases. Routes and empty/loading/error are real.

**SPA (single-page app)** — one JavaScript app. Clicking a video does **not** reload the whole site. FastAPI stays the server. The browser is only a client.

**Vite** — the tool that starts the React app and rebuilds when you edit. Not an AI. Not the API.

**React** — the library that draws the screens from data (list of videos, error, empty).

**TypeScript** — JavaScript plus types. Catches “this video has no duration” mistakes before you click.

**Next.js** — React **plus** its own Node server (SSR). We already have FastAPI. Two servers is extra for this demo.

**CSS modules** — a `.css` file next to a component. Class names stay private. Still normal CSS (`color`, `padding`).

**Tailwind** — tiny classes in the HTML (`flex`, `p-4`). Fast if you already like it. Extra install and a different way of writing style.

**react-router** — `/` vs `/videos/abc`. Two URLs, two screens.

**`VITE_API_URL`** — env var: “FastAPI lives here” (e.g. `http://127.0.0.1:8000`).

**Empty / loading / error** — no videos yet; waiting on the network; API is down or the id is missing. The app must not go white-screen.

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

## Options (read these, then answer)

This phase only picks **how we build the website**. Not upload, not chat.

### 1. App kit — what draws the screens

| Option | What it is | Cost | When it wins |
|---|---|---|---|
| **A. Vite + React + TypeScript** (my pick) | SPA in `web/`. Talks to FastAPI with `fetch`. | Small. One extra folder. | This product: Python does ML, browser does UI. |
| **B. Next.js** | React + a Node server that can render HTML on the server. | Two backends (Next + FastAPI). Deploy story gets messy. | SEO, or if we had **no** FastAPI. We have FastAPI. |
| **C. Vue or Svelte** | Same SPA idea, different library. | Fine technically. | Only if you already live in that world. |
| **D. Plain HTML + a bit of JS** | No React. | Cheap day one. Painful once chat and a player share state. | A one-file mock. Not the complete app. |

**Pick A unless you say otherwise.** We are not calling Gemma from the browser. We are not doing server-rendered marketing pages.

### 2. Style — how it looks

| Option | What it is | Cost | When it wins |
|---|---|---|---|
| **A. CSS modules** (my pick) | `Library.module.css` next to `Library.tsx`. Normal CSS. Names don’t leak. | Zero new toolchain. | Simple UI, two pages. |
| **B. One global `.css` file** | All classes in one place. | Simplest file count. | Tiny pages. Name clashes (`title` vs `title`) show up as we grow. |
| **C. Tailwind** | Utility classes in JSX. | Extra config, new vocabulary. | If you already think in Tailwind / want shadcn later. |
| **D. MUI / shadcn / Chakra** | Ready-made buttons and themes. | Heavy. Fights a “small demo” look. | Design-system product. We are not that. |

**Pick A.** Phase 12 can still make it work on a phone with the same CSS. Tailwind is the swap if you hate writing CSS.

### 3. Routes — which URLs

| Option | URLs | Why |
|---|---|---|
| **A. `/` + `/videos/:id`** (my pick) | Library. One video. | Matches the two jobs: pick a file, then watch+ask. |
| **B. Only `/`** | Everything on one page. | Player + list + chat in one scroll gets messy. |
| **C. Extra `/upload`** | Third route now. | Upload is Phase 10; can stay a button on `/` later. |

**Pick A.** Phase 10 can put “Upload” on the library. Phase 11 fills `/videos/:id`.

### 4. Talking to FastAPI

| Option | What it is | Why not / why |
|---|---|---|
| **A. Thin `fetch` + `VITE_API_URL`** (my pick) | One small `api.ts`. | This phase is two GETs. |
| **B. axios** | Same as fetch, extra package. | No win. |
| **C. React Query / SWR** | Cache, retries, spinners for you. | Nice later if chat polling gets noisy. Not needed for a list. |
| **D. Fake list in React state** | Pretty screens, no backend. | Lies. Curl-uploaded videos would not appear. |

**Pick A + real `GET /videos`.** API down → error state (don’t crash). Missing video id → error on the watch page.

Dev: either `VITE_API_URL=http://127.0.0.1:8000` (CORS already open) or Vite proxy `/api` → FastAPI. Same client. Agent can pick proxy for less CORS fuss.

### 5. Things that are **not** options this phase

| Topic | Locked already / later |
|---|---|
| Auth / login | **None** (backend has none). |
| Player | Phase 11 (`<video>`). |
| Chat box | Phase 11 (`POST /chat`). |
| Upload button | Phase 10. |
| Calling Gemma from the browser | Never. Browser → FastAPI only. |

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

Answer with the letter, or “yes” to take my picks (A, A, A, A).

1. **App kit:** A Vite+React+TS · B Next.js · C Vue/Svelte · D plain HTML  
   I would take **A**.
2. **Style:** A CSS modules · B one global CSS · C Tailwind · D MUI/shadcn  
   I would take **A**.
3. **Routes:** A `/` + `/videos/:id` · B one page · C extra `/upload` now  
   I would take **A**.
4. **API:** A real `GET /videos` + thin fetch · B axios · C React Query · D fake list  
   I would take **A**.

When these are answered, mark **LOCKED**. Next is the upload form (Phase 10).

## Done when

- Open `/` → empty or a list from the API
- Navigate to a video page shell
- API down → error state, app does not crash
- No upload, no player, no chat yet
