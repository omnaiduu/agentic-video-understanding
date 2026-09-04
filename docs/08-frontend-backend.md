# Frontend and backend

Frontend was **not** locked in the earlier thread. This is the plan that fits the decisions.

## Backend

**Demo stack (what we run locally):** Node on the laptop is the API. Models stay on **Modal** in Python. Detail and algorithms: [20-backend-algorithm.md](20-backend-algorithm.md).

| Piece | Choice | Why |
|---|---|---|
| Product API | **Node** (local) | HTTP, in-memory session, ffmpeg, calls Modal |
| ML | **Python on Modal** | Whisper, SigLIP, GLAP, **ColQwen**, Gemma cannot run in Node |
| HTTP | Node `/videos` + `/chat` | Upload, ingest status, questions |
| Media | **ffmpeg** CLI on the laptop | Cut frames/audio/clips |
| Brain | OpenAI-compatible calls to **Modal** Gemma E4B | Two calls: **plan** (form) and **answer** (short slice) |
| Auth | **None.** Refresh clears chat | Demo only; one user |
| Ingest workers | Modal jobs from **zero** | WhisperX (English, diarization on) / SigLIP / GLAP / **ColQwen** |

Main Gemma sees **last ~8 user messages** (what they typed) **plus the notepad** (the clock, e.g. 1:04). User text alone cannot fill times.

### API sketch (v1)

- `POST /videos` — upload or register path; start ingest
- `GET /videos/{id}` — status: processing | ready | error
- `POST /videos/{id}/chat` — message; returns answer, citations `{t}`, **transcript quotes**, **frame URLs**, live **status** events, export URLs
- `GET /videos/{id}/exports/{file}` — or public object-storage URLs

### Data

| Store | Holds |
|---|---|
| **Memory** | chat, sticky note, messages (gone on refresh) |
| **Owner disk** | original mp4, ffmpeg cuts, export files |
| **Modal** | four books + Gemma |

Postgres + pgvector when there are many users/videos — not day one.

### Session

Persist a **clipboard** per chat: `handle_id`, **focus** window `{t0,t1}`, last search hits (talk/look/listen/**slides**), one-line notes. Follow-up “was a car in that frame?” uses focus — no re-search. Combo questions update focus in order (`shift_after`). See [16-clipboard-and-verbs.md](16-clipboard-and-verbs.md).

## Frontend

**Job:** upload (or pick a file), show ingest progress, chat, show timestamps (click to seek), show exported clip/audio links, empty/error/loading states.

**Proposed v1 demo UI:** **one page**, desktop first. Upload **or paste mp4 URL**. Spinner + **live status** (searching / cutting / reading). Answer shows **text, timestamps, transcript quote, the frame(s)**. Audio-only files OK. One chat, one video.

Why not Next.js as a must: we never chose it; a SPA against FastAPI is enough. Swap later if we need SSR.

Screens:

1. Library — videos, ingest status
2. Watch + ask — player, thread, timestamp chips, “download clip”
3. Empty: no video yet
4. Error: ingest failed / model down

Desktop + mobile: player + chat stack on small screens.

## ffmpeg vs MediaBunny vs Node vs Go

- **ffmpeg:** backend cutter. Locked.
- **MediaBunny:** browser trim/preview later; not the ML path.
- **Node:** **demo API** (orchestrator). Not the ML worker.
- **Go:** later high-QPS cut service; not v1.

## Local vs Modal

- **Dev / demo:** Node + ffmpeg on the laptop; video **on disk**; Gemma + ingest on **Modal** (~$30/mo, E4B only, scale to zero). Chat is **in-memory** (refresh = gone). Record a screen video.
- **Prod (later):** same split, or move the Node API next to Modal; files on Volume/S3.

## Resources / throughput (honest ranges)

- E4B 4-bit: more concurrent chats on one L4.
- 12B 4-bit: typical **search + 20 frames + 2–4 tool rounds** often **~10–40s**, GPU-bound.
- FAISS/CLAP query: milliseconds.
- ffmpeg 5s export: sub-second to a few seconds.
- Bottleneck = **Gemma + frames**, not SQLite.
