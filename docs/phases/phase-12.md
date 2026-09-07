# Phase 12 — Clips and polish

**Status:** not locked. Human answers the questions at the bottom first. **Last phase.** After this, the complete app is specified.

Depends on: [Phase 7](phase-07.md) (`export_url`, `GET /videos/{id}/exports/{id}`), [Phase 11](phase-11.md) (watch + ask). Same TanStack Start + shadcn app.

Product (short): show **clip/audio links**, make the page work on a **phone**, make errors **readable**, write how to run the app.

Related: [phase map](../12-build-phases.md) · [rejected](../04-what-we-rejected.md)

---

## Where we are

| Done on paper | This phase |
|---|---|
| Backend 1–8 + website 9–11 (upload, play, ask, seek) | **Take-away file + phone + copy** |

Not a new product. Finish the one app.

---

## What we are trying to do

When chat includes an `export_url` (Gemma asked `export_clip` / `export_audio`):

- Show a **Download** (and maybe play the short file).
- Fetch is `GET /videos/{id}/exports/{export_id}` — already locked. No auth.

On a **narrow screen**: player **above**, chat **below** (don’t squeeze them side by side).

Errors a human can read:

- No videos yet (Phase 9 empty)
- Upload / ingest failed (`error_message`)
- API / Gemma unreachable
- Export too long (60s reject from Phase 7)

Root README: how to run **FastAPI + `web/`** together.

---

## What this is not

- **Not** login, users, signed URLs.
- **Not** `crop_frame` / `ocr_frame` / `search_notes` / scene detect / training E2B.
- **Not** a second app. Same `web/` + FastAPI.
- **Not** Elasticsearch. DB is already Postgres.

---

## Words

**Clip link** — URL to the short mp4/wav from Phase 7. For the human, not for Gemma.

**Stack** — on a phone, blocks go top-to-bottom: player, then chat.

**Polish** — empty / error / loading copy, not a redesign.

---

## How it will work

```
Chat answer
  text
  time chips (Phase 11)
  if export_url → Button “Download clip” (and optional <video> / <audio> for that URL)

Width < ~768px
  player full width
  chat full width under it
```

Delete video: Phase 1 `DELETE` exists. UI button is optional (see questions).

---

## Options (what I would pick)

| Topic | My pick | Other options | Why my pick |
|---|---|---|---|
| Clip UI | **Download button** + **small inline player** for the export | Download only; or open in a new tab | You should hear/see the cut without leaving. Download is the take-away. |
| Phone | **Stack under ~768px** (Tailwind `md:`) | Same side-by-side always | Watch+ask on a phone is unusable side by side. |
| Delete in UI | **Button on the watch page** (confirm, then `DELETE /videos/{id}`, back to `/`) | Library-only; or no UI delete (curl only) | You wanted demo files not to live forever. Explicit delete, not auto-wipe on “bye”. |
| README | **Root README**: backend + web commands | Docs-only | Someone cloning the repo should run both. |

---

## Plan (agent)

1. Render `export_url` as Download (+ inline short player)
2. Responsive stack: player then chat on small width
3. Copy for empty, ingest error, model/API down, export-too-long
4. Optional delete control if we lock it
5. Root README: Postgres, FastAPI, `web/` (Start), env vars (`DATABASE_URL`, `VITE_API_URL`, vLLM)
6. No new ML. No login.

Implement **only** this file after 11.

---

## Questions (lock these)

1. **Clip: Download button + small inline player** for the exported file. OK? (Other: download only.)
2. **Phone: stack player above chat** under ~768px. OK?
3. **Delete video button** on the watch page (confirm → API DELETE → library). OK?
4. **Root README** with run instructions for API + website. OK?

When these are answered, mark **LOCKED**. That is the complete production app on paper.

## Done when (complete app)

A long video from the **website** can: (a) speech question, (b) silent visual, (c) sound question, (d) follow-up without re-ingest, (e) exported clip link, (f) usable on a phone — without loading the whole file into Gemma.
