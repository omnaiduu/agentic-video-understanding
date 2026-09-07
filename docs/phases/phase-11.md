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

**Player** — the box that plays the file. Play / pause / scrub. Built into the browser.

**Seek** — jump to 1:04 when the answer says 1:04.

**`session_id`** — nametag for this chat on this video. Same tag → “that frame” still works (Phase 8).

**Working…** — Gemma may look/listen several times. The API sends **one** answer when it is done. The page waits.

**Tool trace** — a list of steps (look at 10s, search “pricing”). For debugging, not the main answer.

**SSE** — stream words as they appear. We do **not** have that API. The loop finishes, then JSON.

**Export link** — “download this 8-second clip.” API can already make it. Showing the button is Phase 12.

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

## Options (read these, then answer)

This phase only picks **how watch + ask feels**. Not clip downloads. Not phone layout.

### 1. Player — what plays the file

| Option | What it is | Cost | When it wins |
|---|---|---|---|
| **A. Native `<video>` / `<audio>`** (my pick) | The browser’s own player. `src` = FastAPI `GET /videos/{id}/file`. | Zero extra library. Range seek already in Phase 1. | This demo. |
| **B. video.js / Media Chrome** | Fancier controls, themes, extra buttons. | Another package. Same file underneath. | Later polish if native looks ugly. |
| **C. Copy the file into `web/public`** | Player loads a static path, not the API. | Duplicates the file. Breaks DELETE. | Never. Phase 1 already streams. |

**Pick A unless you say otherwise.** Audio-only files use `<audio>`. Chat still works.

### 2. Session — does “that frame” survive refresh?

| Option | What it is | Cost | When it wins |
|---|---|---|---|
| **A. Keep `session_id` on the page + localStorage per video** (my pick) | First answer returns an id. We save it. Next questions send it. Refresh → same chat. | Tiny. | Follow-ups were Phase 8’s whole point. |
| **B. Keep it only in memory** | Refresh starts a **new** chat. Indexes do not rebuild; the **thread** is new. | Simpler. | If you want a clean slate every load. |
| **C. New `session_id` every message** | Every question forgets “that.” | Breaks Phase 8 in the UI. | Don’t. |

**Pick A.** Closing the tab later is fine; it is only in that browser.

### 3. Timestamps — what a time in the answer does

| Option | What it is | When it wins |
|---|---|---|
| **A. Chips you click → player jumps** (my pick) | Answer “at 1:04” is a button. Click → 1:04. | The product. |
| **B. Plain text “1:04”** | You scrub by hand. | Worse. |
| **C. Auto-seek with no click** | Every answer yanks the playhead. | Annoying if you were watching. |

**Pick A.**

### 4. Waiting, trace, clip links (one bundle)

The backend today: think → look/listen/search → **then** one JSON. Not word-by-word.

| Piece | A (my pick) | Other | Why A |
|---|---|---|---|
| While the API thinks | Disable send. Show **Working…** | SSE / fake typing | SSE needs a new backend. Fake typing lies. |
| Tool trace (`steps`) | **Collapsed “details”** | Hide forever, or always show | Useful when it looks stuck. Not the headline. |
| `export_url` in the answer | **Hide until Phase 12** | Show a download button now | Phase 12 is clip links + phone. |

You can mix (e.g. hide the trace but keep Working…). Default is A for all three.

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

Answer with the letter, or “yes” to take my picks (A, A, A, A).

1. **Player:** A native `<video>`/`<audio>` from FastAPI · B video.js · C copy file into the web app  
   I would take **A**.
2. **Session:** A save `session_id` (page + localStorage) · B forget on refresh · C new id every message  
   I would take **A**.
3. **Times:** A click to seek · B plain text · C auto-jump with no click  
   I would take **A**.
4. **Wait / trace / clips:** A Working… + collapsed details + hide downloads until Phase 12 · mix if you say  
   I would take **A**.

When these are answered, mark **LOCKED**. Last phase is clips + phone polish.

## Done when

- Ask a question on a ready video; see answer text
- Click a time; player jumps there
- Follow-up on the same page uses the same session
- Audio-only still chats
- No clip-download UI yet
