# Backend: how it actually runs (Node local, models on Modal)

This is the **working plan** for a demo you run on your machine, with a few models on **Modal**. Not locked as production forever. Record a screen demo when the five checks at the bottom pass.

Older short notes: [18-the-plan.md](18-the-plan.md) (form), [19-three-speeds.md](19-three-speeds.md) (three speeds). This page is the **algorithm** — who does what, in what order, with what data.

---

## Two memories (added to the plan)

Words like **“there”**, **“that”**, **“the clip”** live in the **chat**.  
Times like **1:04** do **not**. You never type them. Search finds them.

So every Gemma “think” call gets **both**:

| Memory | What it is | Example |
|---|---|---|
| **Chat (user text)** | Last ~8 things **you** typed. Not a dump of tool logs. | “When did they clap?” then “Was there a dog there?” |
| **Notepad (state)** | One small JSON row Node saves | `focus: 1:04–1:12`, `tried: ["listen:clap"]` |

A **main** Gemma call reads those and fills the **form** (jobs + search words + sure/not sure).  
It does **not** search the video. It does **not** pick FPS. It only says **what this turn is**.

If we fed **only** raw user text, “there” would have no clock. The notepad is the clock.

---

## Who lives where

```
Your laptop (Node)
  UI  (browser)
  API (Node)          ← traffic cop: form, speeds, notepad, ffmpeg
  SQLite              ← videos, chats, notepad, cached search hits
  ffmpeg              ← cut frames / audio / clips
  video files         ← local disk (demo)

Modal.com (Python + GPU)
  Gemma E4B           ← fill form (text) + read short slices (pictures/sound)
  WhisperX            ← speech book at upload
  SigLIP 2            ← picture book at upload
  GLAP                ← sound book at upload
  ColQwen / ColPali   ← slide book at upload (unique slides only; on-screen text)
```

**Why Node here:** you asked for Node for the demo. Node is good at HTTP, files, SQLite, calling ffmpeg, calling Modal.

**Why not Node for Whisper/Gemma:** those models are Python. Modal runs them. Node only sends JSON and files.

**Why ffmpeg on the laptop:** cutting 8 seconds is a local CLI job. No GPU.

---

## The pieces in one sentence each

1. **Upload** — save the mp4, start ingest on Modal, wait until **four** books exist (speech, pictures, sounds, **slides**).  
2. **Books** — speech / pictures / sounds / **slides (ColQwen)**. Built **once**. Question 2 reuses them.  
3. **Notepad** — where we are on the timeline, last hits, already tried, last answer.  
4. **Main Gemma** — reads **your last messages + notepad**, fills a **form**.  
5. **Speeds** — Node code (not Gemma) picks ready-made / many jobs / hunt.  
6. **Tools** — Node asks Modal to search, or runs ffmpeg to cut, then updates the notepad.  
7. **Answer Gemma** — sees the notepad + a **short** slice, writes the user-facing answer.  
8. **Caps** — max 3 form-fills, short zooms, count in code, then stop.

---

## Data we store (the state)

One SQLite database on the laptop.

### Video row

```
id, path, duration_sec, ingest_status   # processing | ready | error
```

### Notepad (one row per chat)

```
chat_id
video_id
focus_t0, focus_t1, focus_why     # “the place we’re talking about”
hits_talk, hits_look, hits_listen, hits_slides
opened_frames, opened_audio       # true/false this turn
tried                             # ["listen:clap", "look:dog"]
notes                             # one line
last_user, last_answer
```

### Chat messages

```
chat_id, role, text, created_at
```

We send Gemma **user texts only** from this table (last 8), plus `last_answer` from the notepad (one short string), **not** every tool trace.

### The form (Gemma output, not stored as source of truth)

```
intents:  ["listen", "look"]           # can be several
verbs:    ["search_listen", "shift_after", "open_eyes"]
queries:  { "listen": "clap", "look": "slide" }
sure:     "sure" | "mixed" | "not_sure"
done:     false
refers_to: "focus" | "new"             # “there” vs a new thing
```

Server **grammar** (constrained JSON) so E4B cannot invent field names.

---

## Constants (caps)

```
MAX_PLANS          = 3          # form-fills per user question
ZOOM_SEC           = 8          # open_eyes window
AUDIO_SEC          = 15         # open_ears window (Gemma ears ~30s max)
MAX_FRAMES         = 32
EXPORT_MAX_SEC     = 60
SKIM_FPS           = 0.25       # last-resort hunt only, code-owned
USER_HISTORY       = 8          # last user messages into main Gemma
SEARCH_TOP_K       = 8
COUNT_MERGE_GAP    = 0.4        # seconds; nearer than this = one event
```

Node **always** clamps times. Gemma never chooses FPS or a 2-hour window.

---

## Algorithm A — upload (once per file)

```
1. User drops an mp4 in the UI.
2. Node saves it, creates video row, status = processing.
3. Node POST to Modal ingest with the file (or a Volume path).
4. Modal:
     a. ffmpeg: duration, has_audio
     b. WhisperX → words + times  → speech book
     c. 1 photo/sec → SigLIP 2    → picture book
     d. 1–5s audio chunks → GLAP  → sound book
     e. dedup unique slides → ColQwen / ColPali → slide book
        (on-screen text nobody spoke; see docs/14)
5. Modal returns “ready” (books stay on Modal Volume; Node may cache
   transcript lines in SQLite for FTS if we want local talk search).
6. Node sets status = ready. UI can chat.
```

Question 2 **must not** run step 4 again.

---

## Algorithm B — one user question (the whole loop)

This is the heart. Same every time.

```
on POST /videos/:id/chat  { text }

0. Load notepad for this chat. Append user text to messages.
   Build prompt_pack:
     - last 8 user texts
     - notepad (focus, hits, tried, last_answer)
     - video duration
     - this new text

1. MAIN (Gemma on Modal, text only)
     → form  (intents, verbs, queries, sure, refers_to)

2. If refers_to == "focus" and notepad has a focus:
     keep focus (follow-up like “there”)
   If refers_to == "new":
     we will search; old focus may be replaced after hits

3. PICK SPEED (Node, no model)
     if form.sure == not_sure:           speed = 3 hunt
     else if intents.length >= 2
          or verbs.length >= 3:          speed = 2 many
     else:                               speed = 1 ready

4. ACT
     speed 1 → RUN_VERBS(form) once
     speed 2 → SORT_VERBS then RUN_VERBS(form) once
     speed 3 → HUNT (below)

5. If speed 1 or 2 and all searches empty and plans_used < MAX_PLANS:
     jump to HUNT  (wrong word / wrong book)

6. ANSWER (Gemma on Modal)
     input: question + notepad + opened frames/audio (if any)
     output: user text + timestamps we already know
     save last_answer on notepad
     return to UI
```

**Main Gemma does not call tools.**  
**Answer Gemma does not pick tools.**  
**Node calls tools.**

---

## Algorithm C — pick speed (exact rules)

```
function pickSpeed(form, notepad, lastSearchEmpty):
  if lastSearchEmpty:                 return HUNT
  if form.sure == "not_sure":         return HUNT
  if form.intents has 2+ items:       return MANY
  if form.verbs has 3+ items:         return MANY
  if form.intents is [export]
     and notepad.focus exists:        return READY   # just cut
  if form.refers_to == "focus"
     and notepad.focus exists:        return READY   # follow-up
  return READY
```

Ready-made jobs (speed 1) are just **common verb bundles**. Node can add missing verbs if Gemma forgot an obvious one:

| Job | If Gemma said this | Node ensures these verbs |
|---|---|---|
| Talk | `talk` | `search_talk` |
| Look | `look` | `search_look` then `open_eyes` on best hit |
| Listen | `listen` | `search_listen` then optional `open_ears` |
| Slides | `slides` | `search_slides` then `open_eyes` (ColQwen finds; Gemma reads) |
| Count | `count` | `search_*` + `count_hits` (no Gemma arithmetic) |
| Export | `export` | `export` on focus (search first if no focus) |
| Follow-up | `refers_to=focus` | `reuse_focus` + `open_eyes` or `open_ears` |

That “ensure” step is why a small model can miss a checkbox and we still run a sane path.

---

## Algorithm D — sort verbs (speed 2)

Gemma may tick boxes in a messy order. Node **rewrites** order:

```
1. reuse_focus          (if any)
2. search_talk, search_look, search_listen, search_slides   (can run in parallel)
3. count_hits
4. shift_after          (needs a hit first)
5. open_eyes, open_ears
6. export
```

Example: Gemma sends `[open_eyes, search_listen, shift_after]`.  
Node runs: search_listen → shift_after → open_eyes.

---

## Algorithm E — run one verb (the tools)

Each checkbox → one Node function. Caps inside.

| Verb | Node does |
|---|---|
| `search_talk` | Modal/SQLite FTS with `queries.talk`. Save hits. Append `tried`. |
| `search_look` | Modal SigLIP search with `queries.look`. Save hits. |
| `search_listen` | Modal GLAP search with `queries.listen`. Save hits. |
| `search_slides` | Modal ColQwen search with `queries.slides` (on-screen text). Save hits. |
| `reuse_focus` | Do not search the whole tape. Keep `focus`. |
| `shift_after` | `focus = [best_hit.t, best_hit.t + ZOOM_SEC]` (move **forward**) |
| `open_eyes` | ffmpeg frames on `focus` (≤ ZOOM_SEC, ≤ MAX_FRAMES). Send paths to answer call later. |
| `open_ears` | ffmpeg wav on `focus` (≤ AUDIO_SEC). |
| `count_hits` | merge hits closer than `COUNT_MERGE_GAP`, `count = length`. **Not Gemma.** |
| `export` | ffmpeg clip on `focus`, cap `EXPORT_MAX_SEC`, save file, URL. |
| `unsure` | run talk+look+listen+**slides** searches **in parallel**. |

After every verb: write notepad to SQLite.

**Find vs understand vs export stay separate.** Search scores are not the answer. Gemma still looks at a short slice when we opened eyes/ears.

---

## Algorithm F — hunt (speed 3, the tiny loop)

```
function hunt(question, notepad, firstForm):
  plans = 1 if we already ran a failed ready/many else 0

  loop:
    if plans >= MAX_PLANS: break

    # 1. Pin evidence (cheap, all four books)
    parallel:
      search_talk(firstForm.queries.talk or question)
      search_look(firstForm.queries.look or question)
      search_listen(firstForm.queries.listen or question)
      search_slides(firstForm.queries.slides or question)
    write all hits onto notepad as sticky notes
    mark tried

    if all four empty:
      optional: SKIM a few frames at SKIM_FPS across the file (code, not Gemma)
      if still empty: break

    # 2. Main Gemma AGAIN — now it sees hits, not a blank map
    form2 = MAIN(question, user_history, notepad)
    plans += 1

    # 3. Act on form2 (sorted verbs) — usually open_eyes/ears on a hit time
    RUN_VERBS(form2)

    if we opened a slice or we have strong hits: break
    # else loop once more

  return notepad
```

Hunt is **not** “Gemma, here are eight tools, go.”  
Hunt is: **search all books → show hits → fill the form again.**

---

## Algorithm G — count (no model math)

```
hits = search_audio("clap")           # or talk/look
sort by time
merged = []
for h in hits:
  if merged is empty or h.t - merged.last.t > COUNT_MERGE_GAP:
    merged.append(h)
  # else: same clap, skip
answer_count = merged.length
spot_check: open_ears on 2 merged times so Gemma can say “yes those are claps”
if hits are a long blob (many seconds): 
  say “applause 1:00–1:40”, do not invent 47
```

---

## Algorithm H — answer call

```
Gemma E4B (vision/audio) on Modal
  sees:
    - user question
    - last 8 user texts (so “there” still makes sense)
    - notepad (times, counts, notes)
    - 0–N frames and/or a short wav
  must:
    - use notepad times in the reply
    - not invent a time we never searched
    - if nothing found: say we could not find it, list `tried`
```

Then Node saves `last_answer` and returns JSON to the UI:

```
{
  "text": "They clapped at 1:04. After that the slide says Q3 plan.",
  "timestamps": [64.0, 68.0],
  "export_url": null,
  "trace": ["search_listen", "shift_after", "open_eyes"]  // for the demo screen
}
```

---

## Modal endpoints (Python)

Keep these small and boring. Node is the brain of the **path**. Modal is the **models**.

| Endpoint | Does |
|---|---|
| `POST /ingest` | WhisperX + SigLIP + GLAP for one video |
| `POST /search/talk` | query → `[{t, text, score}]` |
| `POST /search/look` | query → `[{t, score}]` |
| `POST /search/listen` | query → `[{t, score}]` |
| `POST /search/slides` | query → `[{t, score, slide_id}]`  ColQwen on unique slides |
| `POST /gemma/plan` | `{question, user_history, notepad}` → form JSON |
| `POST /gemma/answer` | `{question, user_history, notepad, frames[], audio?}` → answer text |

Gemma is **two** calls with two prompts: plan (text) and answer (multimodal). Same weights, different input.

---

## Node endpoints (local demo)

| Endpoint | Does |
|---|---|
| `POST /videos` | upload mp4, kick ingest |
| `GET /videos/:id` | status |
| `POST /videos/:id/chat` | Algorithm B |
| `GET /videos/:id/exports/:file` | download clip |

UI: one page is enough for the demo — pick/upload video, wait until ready, chat, click timestamps, download clip.

---

## Worked example (every step)

Video is a 20-minute talk. Books are ready. Notepad is empty.

### Turn 1 — “When did they clap?”

1. **User history:** `["When did they clap?"]`  
   **Notepad:** empty.

2. **Main Gemma** form:
   ```
   intents: [listen]
   verbs: [search_listen]
   queries: { listen: "clap" }
   sure: sure
   refers_to: new
   ```

3. **Speed 1.** Node also ensures optional `open_ears` if we want a confirm.

4. `search_listen("clap")` → `{ t: 64.0, score: 0.81 }`  
   Notepad focus = 64–72. tried = `listen:clap`.

5. **Answer Gemma** (maybe 2 seconds of audio): “Clap at 1:04.”  
   UI shows timestamp chip **1:04**.

### Turn 2 — “What was on the slide after that?”

1. **User history:**  
   `["When did they clap?", "What was on the slide after that?"]`  
   **Notepad:** focus 64–72, last_answer “Clap at 1:04.”

2. **Main Gemma** understands “after that” from **chat**, and 1:04 from **notepad**:
   ```
   intents: [listen, look]
   verbs: [reuse_focus, shift_after, open_eyes]
   sure: mixed
   refers_to: focus
   ```

3. **Speed 2.** Sort: reuse_focus → shift_after → open_eyes.  
   `shift_after`: focus becomes 64–72 (already after the clap).  
   ffmpeg: ~8 frames.  

4. **Answer Gemma** sees the frames: “The slide says Q3 plan.”  
   Notepad notes = “clap ~1:04; slide Q3”.

### Turn 3 — “Was there a dog there?”

1. History now includes the dog line. Notepad still 64–72.

2. Main:
   ```
   intents: [look]
   verbs: [reuse_focus, open_eyes]
   queries: { look: "dog" }
   refers_to: focus
   ```

3. **Speed 1 follow-up.** Node does **not** scan 20 minutes.  
   Optional: `search_look("dog")` **near focus only**.  
   Open the same window. Answer: “No dog in that window.”

### Turn 4 — “Give me that clip.”

1. Main: `intents: [export]`, `refers_to: focus`.  
2. Speed 1. ffmpeg 1:04–1:12. Return `export_url`.  
3. Answer: “Here’s the clip.” + link.

### Turn 5 — hunt (“What was that weird noise?”)

1. Main: `sure: not_sure`, weak query.  
2. **Speed 3.** Parallel search all **four** books (speech, pictures, sounds, slides). Sticky notes: beep 12:01, laugh 12:04.  
3. Main again: `open_ears` on 12:01.  
4. Answer: “Microphone beep at 12:01.”  
   If empty after 3 plans: “I couldn’t find it. I tried …”

### Turn 6 — on-screen text nobody spoke (“Which slide had Pro $99?”)

1. Speech book is empty (she never said the number). SigLIP only sees “a slide.”  
2. Main: `intents: [slides]`, `verbs: [search_slides, open_eyes]`, `queries.slides: "Pro $99"`.  
3. Speed 1. `search_slides` (ColQwen on unique slides) → 14:10.  
4. ffmpeg frames. Answer Gemma **reads**: “Pro $99.”  
   ColQwen found the second. Gemma still reads the frame.

---

## Sequence (one picture)

```
Browser  →  Node API  →  SQLite notepad
                │
                ├─ POST Modal /gemma/plan     (history + notepad → form)
                ├─ pickSpeed()                (code)
                ├─ POST Modal /search/*       (books)
                ├─ ffmpeg                     (short cut)
                └─ POST Modal /gemma/answer   (slice + notepad → text)
                │
Browser  ←  answer + timestamps + optional clip
```

Two Gemma calls on a simple question. Three on a hunt (plan, plan again, answer). Never an 8-step free tool loop.

---

## Demo (this is “done”)

Run **Node on the laptop**. Point it at **Modal** with a few deployed functions (Gemma E4B, ingest, three searches). Use one ≥10 minute file.

Record the screen:

1. Upload / pick file → status becomes ready (ingest once).  
2. Speech: “What did she say about …?” → timestamp.  
3. Sound: “When did they clap?” → timestamp.  
4. Follow-up: “Was there a dog **there**?” → does **not** re-ingest, uses notepad.  
5. Combo: “After the clap, what was on the slide?”  
6. Export: “Give me that clip” → download link.  
7. Optional: a vague “what was that noise?” to show hunt.  
8. Slides: “Which slide had Pro $99?” (nobody spoke the number) → ColQwen find → Gemma reads.

That recording is the v1 proof. No production auth, no 12B waiter, no watching the whole file.

---

## What this still will not do

- Invent 1:04 from user text alone (notepad must hold it).  
- Read `$99` without `open_eyes` on that frame.  
- Count 47 claps inside one roar.  
- Translate the whole talk / draw graphs (no verb yet).  
- Survive a book miss (tiny/quiet/too-fast event).

---

## Suggested default for this demo

| Piece | Choice |
|---|---|
| Orchestrator | **Node** (local) |
| Models | **Modal** (Gemma E4B, WhisperX, SigLIP 2, GLAP, **ColQwen slides**) |
| Cutter | **ffmpeg** on the laptop |
| State | **SQLite** notepad + last 8 **user** messages |
| Driver | Main form → three speeds → answer |
| 12B | Not for this demo |
| UI | One watch+ask page, enough to record |

Product to the user is unchanged: ask, timestamp, clip.  
The logic is: **chat tells us what they mean, notepad tells us where we are, four books find (including ColQwen slides), Node presses, Gemma reads a short slice.**
