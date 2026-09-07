# Phase 9 — Website shell

**Status: LOCKED** (TanStack Start + shadcn/Tailwind + TanStack Query; two routes; FastAPI still the API).

Depends on: backend Phases [1](phase-01.md)–[8](phase-08.md) already serving HTTP (`GET /videos`, `GET /videos/{id}`, CORS open).

Product (short): a website exists with the **right screens**, talking to FastAPI, even if upload and chat are still crude.

Related: [frontend plan](../08-frontend-backend.md) · [shadcn + Start](https://ui.shadcn.com/docs/installation/tanstack) · [Start routing](https://tanstack.com/start/latest/docs/framework/react/guide/routing) · [phase map](../12-build-phases.md)

---

## What we are trying to do

Open the site. **Library** lists videos from `GET /videos` (or empty / loading / error). Click a row → **watch+ask shell** (title, status, placeholder panels). API down → error, no crash.

Curl-uploaded videos show up. No upload form. No player. No chat. Browser never talks to Gemma.

---

## Locked (your picks)

| Topic | Decision |
|---|---|
| App | **TanStack Start** (React + Vite + TanStack Router, file routes) in `web/` |
| Style | **Tailwind** + **shadcn/ui** ([install on Start](https://ui.shadcn.com/docs/installation/tanstack)) |
| Routes | **`/`** library, **`/videos/$videoId`** shell (you did not pick one-page or `/upload`; this is A) |
| Data | **TanStack Query** (`useQuery`) on real FastAPI GETs — not a fake list |
| Auth | **None** |
| ML / files | **FastAPI only.** Start **server functions must not** run ffmpeg, Whisper, SigLIP, CLAP, or Gemma |

**Why Start is OK here:** you asked for it. It is a React full-stack kit (SSR, server functions). We still treat it as the **UI host**. The product API stays Python. Do not grow a second backend.

**Why Query this phase:** you asked. Two GETs still use `useQuery` so Phase 10 can poll ingest with `refetchInterval` on the same client.

---

## Words

**TanStack Start** — React framework on Vite + TanStack Router. File routes, optional SSR. Not FastAPI.

**TanStack Query** — cache + loading/error for fetches. Spinners come from query state.

**shadcn/ui** — copy-paste components (Button, Card, …) on Tailwind. We own the files under `components/ui`.

**Server function** — Start RPC on the Node/Vinxi server. **Forbidden** for media/ML. Allowed only as a thin proxy to FastAPI if CORS is annoying — prefer the browser calling FastAPI directly (`API_URL`).

---

## How it will work

```
web/   TanStack Start
  src/routes/__root.tsx
  src/routes/index.tsx              GET /videos   → library
  src/routes/videos/$videoId.tsx    GET /videos/:id → shell

FastAPI (unchanged)  :8000
```

Env: `VITE_API_URL` or `API_URL` (e.g. `http://127.0.0.1:8000`). CORS already open.

**Library:** Query `GET {API}/videos`. `isPending` → loading. `isError` → error. `data.length === 0` → empty. Else Card list: name, duration, status. Link to `/videos/$id`.

**Watch+ask:** Query `GET {API}/videos/:id`. Show name, duration, status. Placeholders: “Player (Phase 11)”, “Chat (Phase 11)”. 404 / error → message + link home.

shadcn this phase: Button, Card, Badge (status). Do not add a full dashboard kit.

---

## Plan (agent)

1. `web/` via TanStack Start + Tailwind; `shadcn init`; add Button, Card, Badge
2. QueryClient on the root route
3. `lib/api.ts`: `listVideos()`, `getVideo(id)` → FastAPI. Timeout. Typed errors
4. File routes: `/` and `/videos/$videoId`
5. Empty / loading / error / list from Query states
6. README: run FastAPI + `web` together
7. Tests: mock fetch; empty, error, list (no live Gemma)

Implement **only** this file after 1–8. No upload. No `<video>`. No chat POST. No Start server fn that shells ffmpeg.

## Done when

- Open `/` → empty or a list from FastAPI
- Navigate to a video page shell
- API down → error state, app does not crash
- No upload, no player, no chat yet
