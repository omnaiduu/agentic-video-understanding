# Build phases (complete app)

This is **one production app**, built in slices. It is not a v1 toy that we later replace.

Old docs stay. They are the *why* and the *locked product*. This file is the *build order* for an AI agent.

| Read this | For |
|---|---|
| [01 Goal](01-goal-and-context.md) | What the product is |
| [03 Key decisions](03-key-decisions.md) | Locked product choices |
| [05 Architecture](05-architecture.md) | Ingest vs question loop |
| [06 Tools](06-tools.md) | Tool list and caps |
| [07 Models](07-models-and-indexes.md) | Gemma, Whisper, SigLIP, CLAP |
| [08 Frontend/backend](08-frontend-backend.md) | Stack |
| [09 Implementation plan](09-implementation-plan.md) | Original build order (this file replaces it as the agent brief) |
| [11 Glossary](11-glossary.md) | Words |

**How an agent should use this file**

- Do **only** the phase you were told to do.
- Do not skip ahead (no Whisper in Phase 1, no React in Phase 3).
- Leave seams for later phases (folder layout, status field, tool module). Do not implement those later phases.
- When a phase says **LOCKED**, follow it. When it says **OPEN**, stop and ask the human.

**End state (the complete app)**

Upload a long video → indexes built once (speech, pictures, sounds) → ask questions → Gemma uses tools on short slices → timestamped answer → optional clip link → website for upload, player, chat. Second question does not re-ingest.

Backend first (Phases 1–8). Frontend second (Phases 9–12). Same app.

---

## Phase map

| Phase | Name | Adds to the app | Status |
|---|---|---|---|
| 1 | Hold a video | FastAPI + SQLite + save file + duration | **Locking now** |
| 2 | Scissors | `get_meta` / `get_frames` / `get_audio` + caps | Proposed |
| 3 | Brain loop | Gemma calls those tools, `/chat` | Proposed |
| 4 | Speech index | Whisper + `search_transcript` | Proposed |
| 5 | Picture index | SigLIP 2 + `search_visual` | Proposed |
| 6 | Sound index | CLAP/GLAP + `search_audio` + count | Proposed |
| 7 | Export | `export_clip` / `export_audio` + URL | Proposed |
| 8 | Memory | Multi-turn last timestamps | Proposed |
| 9 | UI shell | React app, pages, empty/loading/error | Proposed |
| 10 | Upload UI | Pick file, ingest progress | Proposed |
| 11 | Watch + ask | Player, chat, seek on timestamps | Proposed |
| 12 | Clips + polish | Download links, mobile, errors | Proposed |

---

# Phase 1 — Hold a video

**In one sentence:** the server starts, you can put a video in, you can read back its id, path, duration, and status.

**Not in this phase:** ffmpeg frame cutting, Gemma, Whisper, search, export, website, login.

## What it is doing

A video file has to live somewhere before anything else can cut it or index it. This phase is that shelf.

1. HTTP API process starts.
2. You send a video (how: see OPEN below).
3. The app copies it onto disk under a stable folder.
4. It asks **ffprobe** (comes with ffmpeg) for duration, fps, has_audio.
5. It writes a row in SQLite.
6. `GET /videos/{id}` returns that row.

Later phases hang off this row: indexes, chat, exports.

## Plan (agent checklist)

1. Create `backend/` Python project (`pyproject.toml`).
2. FastAPI app, CORS open (the website in Phase 9 will need it).
3. Config via env / `.env` (`DATA_DIR`, `DATABASE_URL`).
4. SQLite + SQLModel (unless human picks another option).
5. `Video` table and `data/videos/{id}/original.mp4` on disk.
6. `POST /videos` + `GET /videos/{id}` (+ `GET /videos` list, cheap and useful).
7. After save, run ffprobe, set `status=ready` (no indexes yet; “ready” here means *file + meta exist*).
8. Tests with a tiny fixture mp4 (generate with ffmpeg in the test, do not commit a big movie).
9. README in `backend/` with how to run.

## Libraries

| Piece | Library | Why |
|---|---|---|
| HTTP | **FastAPI** + **uvicorn** | Locked in [08](08-frontend-backend.md) |
| Upload parsing | **python-multipart** | FastAPI file uploads |
| Settings | **pydantic-settings** | `DATA_DIR`, later `MODEL_BASE_URL` |
| DB | **SQLModel** (SQLAlchemy + Pydantic) | One style for rows now and chat/transcript later |
| Driver | stdlib **sqlite3** via SQLModel | No Postgres day one ([08](08-frontend-backend.md)) |
| Tests | **pytest** + **httpx** | API tests |
| Duration | **ffprobe** CLI | Same family as ffmpeg; not a Python decoder |

Do **not** add Whisper, transformers, FAISS, React, or a Gemma client here.

## How it is made (layout)

```
backend/
  pyproject.toml
  README.md
  app/
    __init__.py
    main.py          # FastAPI app, CORS, routers
    config.py        # DATA_DIR, DATABASE_URL
    db.py            # engine, session, create_all
    models.py        # Video
    storage.py       # save bytes → data/videos/{id}/original.mp4
    media.py         # ffprobe → duration, fps, has_audio
    routers/
      videos.py      # POST/GET
  tests/
    conftest.py
    test_videos.py
data/                  # gitignored; created at runtime
```

Website folder `web/` is **not** created yet (Phase 9).

## What the code looks like (shape, not copy-paste gospel)

**Row**

```python
class VideoStatus(str, Enum):
    uploaded = "uploaded"
    processing = "processing"
    ready = "ready"
    error = "error"

class Video(SQLModel, table=True):
    id: str                          # uuid4 hex
    original_path: str
    duration_s: float | None = None
    fps: float | None = None
    has_audio: bool | None = None
    status: VideoStatus = VideoStatus.uploaded
    error_message: str | None = None
    created_at: datetime
```

Phase 1 flow: `uploaded` → ffprobe → `ready` (or `error`).  
`processing` is unused until Phase 4 ingest. Keep the value so we do not migrate later.

**Routes**

- `POST /videos` — multipart file (and/or path; see OPEN).
- `GET /videos` — list.
- `GET /videos/{id}` — one video: id, duration, fps, has_audio, status.

No `/chat`. No tool routes.

**Storage path:** `DATA_DIR/videos/{id}/original.mp4`  
Later: `frames/`, `indexes/`, `exports/` under the same `{id}/`.

## Technical decisions (Phase 1)

| Topic | Proposed default | Notes |
|---|---|---|
| Language | Python 3.11+ | Matches [08](08-frontend-backend.md) |
| API folder | `backend/` | Frontend later = `web/` |
| IDs | UUID hex | Stable file names; not 1, 2, 3 |
| Auth | None | Locked for now |
| DB file | `DATA_DIR/app.db` | One SQLite file |
| Probe | ffprobe JSON | Fail → `status=error` + message |
| CORS | Allow all in dev | Tighten later if we ever host a real domain |
| Gitignore | `data/`, `.env`, `__pycache__` | |

## OPEN — human must pick (Phase 1)

**A. How does a video get in?**

- **A1 — Upload only.** `POST /videos` with a file. What the website will use. Tests upload a tiny mp4.
- **A2 — Disk path only.** JSON `{ "path": "/home/me/talk.mp4" }`. Handy on a GPU box. Awkward for the website.
- **A3 — Both.** Upload for the product; path for local/dev. Slightly more code.

**Recommend: A3.** Production path is upload. Path-register keeps local work easy.

**B. Database library?**

- **B1 — SQLModel.** Proposed.
- **B2 — SQLAlchemy only.** Fine, more boilerplate.
- **B3 — raw sqlite3.** Too little structure once transcripts and chats exist.

**Recommend: B1.**

**C. Folder names?**

- **C1 — `backend/` + later `web/`.** Proposed.
- **C2 — `api/` + `frontend/`.** Same idea, different names.

**Recommend: C1.**

When these three are answered, this phase is **LOCKED**. An agent may implement only Phase 1.

## Done when (Phase 1)

- `uvicorn` starts.
- You can add a video and `GET` it back with duration > 0.
- A bad file sets `status=error`.
- Tests pass without a GPU and without extra models.
- No UI, no chat, no frame extraction as a product feature (ffprobe only).

---

# Phase 2 — Scissors

**In one sentence:** the app can cut a **short** picture strip or audio slice from a stored video, and it **refuses** a two-hour dump.

**Depends on:** Phase 1 (a video id and `original_path`).

**Not in this phase:** Gemma, search indexes, export-to-URL, UI.

## What it is doing

ffmpeg is the scissors ([06](06-tools.md)). Gemma is not here yet. We still build the **real** tool functions the brain will call in Phase 3.

Three functions (Python, not public “download the movie” APIs):

| Tool | Does |
|---|---|
| `get_meta(video_id)` | duration, fps, has_audio (from DB / ffprobe) |
| `get_frames(video_id, start, end, fps)` | JPEGs for that window |
| `get_audio(video_id, start, end)` | wav bytes (keep short, ≤ ~30s later for Gemma) |

**Server clamps** (do not trust the caller):

- Max window for frames (e.g. zoom ≤ 8s, or skim with very low FPS).
- Max FPS (e.g. 8–10).
- Max frame count (e.g. 32–64).
- `get_frames(0, 7200, fps=1)` → error or rewrite. Never run it.

## Plan

1. `app/tools/` module: `get_meta`, `get_frames`, `get_audio`.
2. ffmpeg CLI via **subprocess** (not MediaBunny, not a Node cutter — [04](04-what-we-rejected.md)).
3. Shared cap helpers.
4. Tests: fixture video, extract 1s of frames, extract 1s of audio, assert oversize window fails.
5. Optional internal debug routes are OK; they are not the product.

## Libraries

- ffmpeg **CLI** (already needed for ffprobe).
- Pillow only if we need to inspect JPEGs in tests — optional.
- No Gemma.

## How it is made

```
ffmpeg -ss START -i original.mp4 -t DURATION -vf fps=FPS ... frame-%03d.jpg
ffmpeg -ss START -i original.mp4 -t DURATION -vn -ac 1 -ar 16000 slice.wav
```

Return **bytes + timestamps**, not a folder the model has to understand. Phase 3 will turn JPEGs into Gemma image parts.

Store temp files under `DATA_DIR/tmp/` and delete after the call.

## Technical decisions (lock when we reach this phase)

| Topic | Proposed | Option |
|---|---|---|
| How we call ffmpeg | subprocess CLI | vs `ffmpeg-python` wrapper |
| Frame format | JPEG | vs PNG (heavier) |
| Audio format | 16 kHz mono wav | matches Whisper/Gemma-ish audio later |
| Caps | window, fps, frame count as constants in config | |
| Who can call tools | Python functions in `app/tools/` | vs REST for each tool (skip REST as the spine) |

## Done when

Tests prove: short slice works; too-long slice is rejected; original file is unchanged.

---

# Phase 3 — Brain loop

**In one sentence:** you send a question; Gemma may call `get_meta` / `get_frames` / `get_audio`; you get an answer. Still **no** search indexes.

**Depends on:** Phase 2 tools.

## What it is doing

This is the product loop: Think → Act → Observe ([05](05-architecture.md)). For now the only way to “find a time” is that the **user said the time** (“what happens at 0:10?”).

```
POST /videos/{id}/chat  { "message": "What happens at 0:10?" }
  → agent loop (cap ~8 rounds)
  → tools
  → { answer, citations: [{t}], tool_trace }
```

Caps: max tool rounds, max frames per question ([06](06-tools.md)).

## Plan

1. `app/agent/loop.py` — while rounds left: call model, run tool, append result.
2. `app/agent/client.py` — OpenAI-compatible HTTP client (`base_url`, `api_key`, `model`).
3. Register **only** the three tools that exist.
4. Fake / scripted brain in tests (no GPU required to merge).
5. Real Gemma via env (`MODEL_BASE_URL`) — Ollama, vLLM, or Modal. Same client.

## Libraries

| Piece | Proposed | Option |
|---|---|---|
| HTTP to model | **openai** Python SDK (compatible servers) | raw httpx |
| Default model name | Gemma 4 **12B Unified** | E4B as cheaper env override ([07](07-models-and-indexes.md)) |
| Host | Env URL, not hard-coded | Local now, Modal later, **same code** |

Do not dump the whole video into the prompt. Pointer = video id + duration from `get_meta`.

## What the code looks like

```python
tools = [get_meta, get_frames, get_audio]  # JSON schemas for the model
for _ in range(MAX_ROUNDS):
    resp = client.chat(messages, tools)
    if resp.tool_calls:
        for call in resp.tool_calls:
            out = run_tool(call)   # clamps inside tools
            messages.append(tool_result(out))
    else:
        return resp.text
```

Chat rows in SQLite can start here (user + assistant messages) so Phase 8 is an add-on, not a rewrite. If we skip storing messages until Phase 8, `/chat` is stateless besides the video id.

**Proposed:** save messages from Phase 3 (simple `ChatMessage` table). Phase 8 only adds “last timestamps.”

## Technical decisions (lock later)

| Topic | Proposed | Option |
|---|---|---|
| Tests without GPU | FakeBrain that must call `get_frames` for a scripted question | skip real Gemma in CI |
| System prompt | “Search/tools first, short windows, never load 2h” | |
| Where Gemma lives | `MODEL_BASE_URL` | Modal vs Ollama is config, not a fork |
| 12B vs E4B | 12B default, `MODEL_NAME` override | |

## Done when

Scripted test: question at 0:10 → `get_frames` called with a short window → answer returned. Oversize tool call never reaches ffmpeg.

---

# Phase 4 — Speech index

**In one sentence:** ingest runs **Whisper once**; Gemma can `search_transcript` instead of listening to the whole talk.

## What it is doing

Upload (already in Phase 1) starts a job: speech → `{t, text}` lines → SQLite **FTS**. Status goes `processing` then `ready`. Question 2 does not run Whisper again ([01](01-goal-and-context.md)).

Tool: `search_transcript(query)` → `[{t, text, score}]`.

Path: “What did she say about pricing?” → search → maybe `get_frames` to see the slide.

## Plan

1. Ingest worker function (same process first; Modal job later via the same function).
2. **faster-whisper** on `original.mp4`.
3. `TranscriptLine` table + FTS5.
4. Register `search_transcript` on the agent.
5. `indexes.transcript = true` on the video (add a JSON or columns; do not rebuild the video table from scratch).

## Libraries

| Piece | Proposed | Option |
|---|---|---|
| ASR | **faster-whisper** | whisper.cpp |
| Size | **turbo** or **large-v3** | turbo = faster ingest, a bit worse text |
| Job runner | FastAPI BackgroundTasks / `asyncio` | Celery, RQ, Modal function — same ingest function |

## Technical decisions (lock later)

- Whisper model size.
- Chunk/store word-level vs segment-level timestamps (segments are enough).
- If ingest fails: `status=error`, keep the file.

## Done when

A lecture-style fixture: ask a spoken phrase → search returns a time → no full-video Gemma listen.

---

# Phase 5 — Picture index

**In one sentence:** ~1 photo per second → **SigLIP 2** vectors; `search_visual("red light")` returns times.

## What it is doing

Whisper has no eyes. This is the picture phone book ([07](07-models-and-indexes.md)). Still not the answer: Gemma must `get_frames` to verify.

Ingest: ffmpeg 1 FPS → SigLIP → vectors + times, next to the video id.

## Plan

1. Frame sample at 1 FPS (ffmpeg), encode, discard bulk JPEGs after vectors are stored (keep vectors + times).
2. Vector table or sqlite-vec / FAISS file per video or one index with video_id.
3. Tool `search_visual(phrase)`: embed phrase, nearest times.
4. Register tool.

## Libraries

| Piece | Proposed | Option |
|---|---|---|
| Encoder | **SigLIP 2** (Hugging Face / timm) | not 2021 OpenAI CLIP ([04](04-what-we-rejected.md)) |
| Vectors | **sqlite-vec** | FAISS — faster at huge scale, extra file |
| Query | embed text with same SigLIP text tower | |

## Technical decisions (lock later)

- sqlite-vec vs FAISS.
- Keep sampled frames on disk or not (storage vs easier debug). **Proposed: delete JPEGs after embed**; ffmpeg can recreate any time.

## Done when

Silent visual query returns a timestamp without Gemma scanning 2 hours.

---

# Phase 6 — Sound index

**In one sentence:** 1–5s audio chunks → **CLAP/GLAP** vectors; `search_audio("chirp")`; counts happen in **Python**, not in Gemma’s head.

## What it is doing

Picture index will not hear a bird. Whisper will not write “clap.” Same pattern as SigLIP ([05](05-architecture.md) counting section).

```
search_audio → times → merge nearby hits → len() in code
→ optional get_audio on 2–3 samples to verify
```

Stadium applause may be one blob. Honest answer: “applause 1:00–1:40”, not a fake 847.

## Plan

1. Chunk audio 1–5s, embed, store vectors + times.
2. `search_audio(phrase)`.
3. Optional helper `count_events` later ([06](06-tools.md)); for this phase, merge+count in the tool or in Python the agent is instructed to trust.
4. Register tool.

## Libraries

| Piece | Proposed | Option |
|---|---|---|
| Encoder | **LAION-CLAP** | **GLAP** (newer, same tool API) |
| Chunk | 3s default, 1s hop or 3s hop | 1s vs 5s |
| Vectors | same store as visual (sqlite-vec / FAISS) | |

## Technical decisions (lock later)

- CLAP vs GLAP.
- Clap-only detector: **not** this phase ([04](04-what-we-rejected.md)).

## Done when

“When did the bird make a sound?” returns a time from the audio index; Gemma may confirm with `get_audio`.

---

# Phase 7 — Export

**In one sentence:** after times are known, cut a clip or audio file, save it, return an **HTTPS (or local) URL**. Cap length (e.g. 60s).

## What it is doing

Find / understand / **give the user a file** — third job ([05](05-architecture.md)).

Tools: `export_clip(start, end)`, `export_audio(start, end)`.

## Plan

1. ffmpeg write `data/videos/{id}/exports/{export_id}.mp4` (or wav).
2. `GET /videos/{id}/exports/{export_id}` streams the file (Phase 1 local disk). Object storage (S3/R2/Modal Volume) later **behind the same storage interface**.
3. Register tools; duration cap.
4. Chat response can include `export_url`.

## Libraries

- ffmpeg CLI again.
- No new web framework.

## Technical decisions (lock later)

| Topic | Proposed | Option |
|---|---|---|
| Where files live | Local disk + API GET | S3/R2/Modal Volume when we host |
| Max length | 60s | config |
| Auth on URLs | none for now | signed URLs when we add users |

## Done when

Tool returns a URL; fetching it is a playable short mp4/wav; 10-minute request is rejected.

---

# Phase 8 — Memory (multi-turn)

**In one sentence:** follow-up uses the **same video** and **last times** (“was a car in that frame?”) without re-ingest and without searching the whole tape again.

## What it is doing

Google’s `step_list` idea ([02](02-conversation-summary.md)): persist `handle_id` (video + indexes) and last tool timestamps.

## Plan

1. `Session` / `ChatMessage` (if not already from Phase 3).
2. `last_times: list[{start, end, kind}]` on the session.
3. System prompt: prefer last times for “that frame / there / the clip”.
4. `POST /videos/{id}/chat` takes optional `session_id`.

## Libraries

- Same SQLite. No Redis required.

## Technical decisions (lock later)

- How many last windows to keep (e.g. last 3).
- Optional `crop_frame` / `ocr_frame` are **not** this phase ([06](06-tools.md) later list).

## Done when

Two-turn test: find a moment, then a follow-up about “that” moment does not re-run ingest and does not search from scratch if times exist.

---

# Phase 9 — UI shell

**In one sentence:** a website exists with the right screens, talking to the API, even if upload/chat are still wired crudely.

**Depends on:** backend Phases 1–8 already serving HTTP.

## What it is doing

[08](08-frontend-backend.md): library, watch+ask, empty, error, loading. Desktop + mobile stack (player then chat on small screens).

## Plan

1. `web/` Vite + React + TypeScript.
2. React Router: `/` library, `/videos/:id` watch+ask.
3. API client (`VITE_API_URL`).
4. Empty / loading / error components. Library can list `GET /videos`.
5. No need for a design system. Simple CSS (see options).

## Libraries

| Piece | Proposed | Option |
|---|---|---|
| App | **Vite + React + TS** | Next.js — not required ([08](08-frontend-backend.md)) |
| Routing | **react-router** | |
| Style | **plain CSS** or **CSS modules** | Tailwind |
| Player | later (Phase 11) | |

## Technical decisions (lock later)

- CSS vs Tailwind.
- Whether library is usable with videos created only via API/curl (yes).

## Done when

Open `/`, see empty or a list from the API. Navigate to a video page shell. No crash if API is down (error state).

---

# Phase 10 — Upload UI

**In one sentence:** pick a file in the browser, see **processing → ready** (or error).

## What it is doing

`POST /videos` multipart + poll `GET /videos/{id}`. This is why Phase 1 upload exists.

## Plan

1. File input, upload progress (bytes).
2. Poll status until `ready` or `error`.
3. Show ingest failure message.

## Libraries

- Same React app. `fetch` or a thin wrapper. No extra upload SDK.

## Done when

Upload a short mp4 in the UI; status becomes ready; it appears in the library.

---

# Phase 11 — Watch + ask

**In one sentence:** play the video, type a question, see the answer, click a **timestamp** to seek.

## What it is doing

The human loop: watch and ask. Player uses `GET` of the original (need a media route if files are not public — add `GET /videos/{id}/media` if missing).

## Plan

1. HTML5 `<video>` (simple).
2. Chat panel: messages, input, waiting state.
3. `POST /videos/{id}/chat`.
4. Timestamp chips → `video.currentTime = t`.
5. Optional: show tool_trace behind a “details” disclosure (debug, not required).

## Libraries

| Piece | Proposed | Option |
|---|---|---|
| Player | native `<video>` | video.js / Media Chrome later |
| Media URL | FastAPI streams `original.mp4` | |

## Done when

Ask a question on a ready video; see answer text; click a time; player jumps there.

---

# Phase 12 — Clips + polish

**In one sentence:** show **clip/audio links** from export tools; layout works on a phone; ingest/model-down errors are readable.

## What it is doing

Finish the complete app, not a new product.

- Render `export_url` as download / inline play.
- Stack player + chat on small width.
- Copy for: no video, ingest error, model unreachable.
- README at repo root: how to run backend + web.

## Not in this phase (still later / never)

- Login, Postgres, Elasticsearch.
- `search_notes`, scene detect, train E2B as CLIP ([04](04-what-we-rejected.md)).
- `crop_frame` / `ocr_frame` unless we already failed on tiny objects / slides.
- Kitchen-sink desktop agent.

## Done when (complete app)

A ≥10 minute video can: (a) speech question, (b) silent visual, (c) sound question, (d) follow-up without re-ingest, (e) exported clip URL, (f) all of that from the website — without loading the whole file into Gemma. Same bar as [09](09-implementation-plan.md), plus UI.

---

# Rules for every phase

1. Same repo. Same video id. Same tools module. Grow it; do not start a second app.
2. Indexes are caches. The product is the agent loop.
3. Counting is code on hits, not Gemma memory.
4. If something is **OPEN**, ask the human. Do not invent a second product.
