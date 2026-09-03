# Three speeds: ready-made job, many jobs at once, short hunt

A proposed driver. **Not locked yet.** Same small Gemma (E4B). Same tools. Same three search books. New idea: **Python picks how strict to be**, and the model always has a **notepad**.

Read this if you want both:

- the **cheap, rigid** path (known jobs), and
- the **flexible** path (mixed questions, “I don’t know”, try again)

…without giving a 4B model a free toolbox, and without needing a 12B waiter.

Shorter older notes: [18-the-plan.md](18-the-plan.md) (form), [16-clipboard-and-verbs.md](16-clipboard-and-verbs.md) (notepad + checkboxes), [15-workflows-vs-agents.md](15-workflows-vs-agents.md) (why not a free agent).

---

## The two old ideas (why we need a mix)

**Idea A — Ready-made job (rigid).**  
We already know the common questions: talk, look, listen, count, export, follow-up.  
Python has a recipe for each. Tiny Gemma only says “this is a sound question” and the search word `clap`. Python does the rest.

- Good: cheap, testable, 4B is enough.  
- Bad: “After the clap, what was on the slide, and was there a dog?” is **several** jobs. One recipe breaks. A wrong label sends us into the wrong recipe.

**Idea B — Free loop (like a 12B waiter).**  
The model holds the tools. It thinks, calls a tool, sees the result in memory, calls the next tool, over and over, then answers.

- Good: mixed questions, retries, unknown wording.  
- Bad: a **4B** model is weak at being a project manager. It picks bad FPS, wanders, repeats itself. A **12B** model is better at that job — and that is the cost we are trying not to pay.

**This note:** keep A’s recipes, keep B’s “try again”, give the 4B model a **form** and a **notepad**, never the raw toolbox.

---

## Everyday picture

Imagine a small helper in a library.

1. **Three books** already exist for this video (built at **upload**, once):
   - speech book (WhisperX) — words people said + times
   - picture book (SigLIP 2) — one photo per second, as numbers
   - sound book (GLAP) — short sound chunks, as numbers
2. You ask a question.
3. Tiny Gemma fills a **short form** (not “pick any tool, pick any FPS”).
4. **Python** reads the form and presses the real buttons (search, cut a few seconds, count, export).
5. Both of them share a **notepad**: where we are on the timeline, what we already found, what we already tried.
6. Tiny Gemma looks at a **short** slice (a few seconds of video or sound) and writes the answer.

The helper never watches the whole two-hour tape. The books are the map. The notepad is memory. Python is the hands. Gemma is the eyes/ears on a small piece, and the one who fills the form.

---

## Four things that are always on

These do not change with the three speeds.

| Piece | Who | What it is |
|---|---|---|
| **Books** | Built at upload | Speech, pictures, sounds. Not rebuilt on question 2. |
| **Tools** | Python | The same eight: search three books, open short video, open short sound, export clip/audio, plus “how long is the file”. |
| **Form** | Gemma E4B | Tick jobs, tick steps, write search words, say sure / mixed / not sure. |
| **Notepad** | Python (SQLite) | Focus time, last hits, last Q&A, **already tried**. Sent to Gemma every turn. |

**Intent** = *what kind of question?* Now it can be **more than one**.  
Example: “After the clap, what was on the slide? Give me the clip.” → listen **and** look **and** export.

**Verb** = *one allowed step.* A checkbox. Each checkbox is wired in code to a tool. Gemma cannot invent a new button.

**Notepad** = *context.* Follow-ups like “was there a dog **there**?” need this. The hunt loop needs this too, so we do not search `clap` five times.

---

## The form (many jobs, not one folder)

One JSON form per plan. Server grammar (xgrammar / outlines) so E4B cannot invent fields.

```
intents:   [listen, look, export]     # list, not one label
verbs:     [search_listen, shift_after, open_eyes, export]
queries:   { listen: "clap", look: "slide" }
sure:      mixed                      # sure | mixed | not_sure
done:      false                      # true = skip more plans, go answer
```

A simple question ticks one intent and one or two verbs.  
A combo ticks several. That **is** “run multiple intents.”  
`not_sure` does not mean “become a free agent.” It means “Python, please hunt.”

---

## The three speeds (how Python runs that form)

Same form. Same notepad. **Code** chooses the speed. Gemma does not.

```
                    user question + notepad
                              │
                              ▼
                   Gemma E4B fills the form
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        Speed 1           Speed 2         Speed 3
        Ready-made        Many jobs       Short hunt
        (rigid)           at once         (tiny loop)
              │               │               │
              └───────────────┴───────────────┘
                              │
                              ▼
              Gemma reads the short slice + notepad
                              │
                              ▼
                           answer
```

### Speed 1 — Ready-made job (rigid)

**When:** Gemma is **sure**, and there is basically **one** intent (talk **or** look **or** listen **or** count **or** export **or** follow-up).

**What happens:** Python ignores extra creativity. It runs the known recipe for that job. **No second plan** unless the search comes back empty (then we jump to Speed 3).

| Job | Everyday example | Python does |
|---|---|---|
| Talk | “What did she say about the price?” | Search speech book → maybe open a few frames → Gemma summarizes |
| Look | “When is there a red bird?” | Search picture book → open a short zoom → Gemma confirms |
| Listen | “When did they clap?” | Search sound book → optional short listen → time |
| Count | “How many claps?” | Search → merge nearby hits → `len()` in Python → spot-check 2 clips |
| Export | “Give me that clip” | Cut around the notepad’s focus time (or search first if we have no focus) |
| Follow-up | “Was there a dog **there**?” | Reuse focus → open eyes/ears → yes/no |

This is Idea A. Cheap. Easy to test. 4B only has to label the job and write a search word.

### Speed 2 — Many jobs at once (multi-intent)

**When:** Gemma ticks **two or more** intents, or several verbs, and is not `not_sure`.

**What happens:** One form fill. Python **sorts** the checkboxes into a safe order, then runs them:

1. searches first (talk / look / listen)  
2. then `shift_after` (move “we’re here” forward — “after the clap…”)  
3. then open eyes / open ears on that window  
4. then count  
5. then export  

The model never picks FPS or a two-hour window. The server clamps.

Example: “After the clap, what was on the slide?”

- Form: listen + look; verbs: search listen, shift after, open eyes; word: `clap`
- Python: find clap → move a few seconds forward → cut video → Gemma reads the slide
- Notepad remembers that window for “was there a dog **there**?”

This is the combo fix from [16](16-clipboard-and-verbs.md). Still **no** free tool loop.

### Speed 3 — Short hunt (unknown / empty / messy)

**When any of these:**

- Gemma set `not_sure`
- Speed 1 or 2 search came back **empty**
- The wording is new but still “find a time, then look or listen” (no matching single recipe)

**What happens:** a **tiny** loop. Not eight wanders. Not raw tools.

1. **Pin evidence.** Python searches **all three books at once** (indexes are milliseconds). Top hits go on the notepad as sticky notes: “speech 0:40 pricing”, “sound 1:04 clap”, “picture 1:12 slide”.
2. **Show the notepad to Gemma.** Now the 4B model is not imagining. It is choosing among **real hits**.
3. **Gemma fills the form again.** Example: “open eyes on 1:12; also open ears on 1:04.”
4. Python acts, updates the notepad, including **already tried**.
5. If still empty or still `not_sure`: **one more** hunt round, then stop.

Max **three** form-fills per user question (first plan + two hunts). Then we answer from what we have, or we say we could not find it — and we can list what we tried.

**Why a 4B model can do this:** choosing among sticky notes is a form. Inventing a 7-step tool chain is not. The 12B waiter was good at the second job. We deleted that job.

Optional last resort (**code**, not the model): if every book is empty, Python may grab a **few** frames spread across the file at very low FPS (already in the tool policy as “skim”). Pin those on the notepad. Ask Gemma “any of these look useful?” That is still a form. It is not “watch two hours.”

---

## How Python picks the speed

Gemma does **not** say “run Speed 3.” It only fills `sure` and the checkboxes. Code:

```
if sure == not_sure or last_search_was_empty:
    Speed 3  (hunt)
else if more than one intent, or several verbs:
    Speed 2  (many jobs)
else:
    Speed 1  (ready-made)
```

Follow-up with a live focus time defaults to Speed 1 (`reuse_focus`) unless the user names a **new** thing (“what about the other clap?” → search again).

---

## The notepad (this is the context)

One small row per chat + this video. **Not** the movie. **Not** the full transcript.

```
video_id, duration
focus:     { t0, t1, why }          # “the place we’re talking about”
hits:      talk / look / listen     # last search hits (sticky notes)
opened:    frames? audio?           # did we already show a slice?
tried:     ["listen:clap", "look:dog"]   # so hunt does not repeat
notes:     "clap ~1:04; slide still up"  # one line Gemma wrote
last_user, last_answer
```

Every Gemma call gets: the new question + **this notepad**.  
Python writes the notepad after every verb. The model does not have to remember across calls. **State lives in the database.**

That is how we have “memory like an agent” on a 4B model: the memory is **outside** the model.

---

## Walk-throughs (same system, different speeds)

### 1. Simple — Speed 1

“When did they clap?”

1. Form: intent listen, sure, word `clap`, verb search listen.  
2. Python: sound book → 1:04.  
3. Optional: open a second of audio to confirm.  
4. Answer: “Clap at 1:04.” Notepad focus = 1:04.

### 2. Combo — Speed 2

“After the clap, what was on the slide?”

1. Form: listen + look; search listen, shift after, open eyes.  
2. Python: clap at 1:04 → focus 1:04–1:12 → frames.  
3. Gemma reads the slide.  
4. Notepad keeps that window.

### 3. Follow-up uses the notepad — Speed 1

“Was there a dog **there**?”

1. Form: reuse focus, open eyes (maybe search look near focus).  
2. Python does **not** scan two hours.  
3. Yes/no from those frames.

### 4. Unknown wording — Speed 3

“What was that weird noise in the middle?”

1. First form: `not_sure`, maybe a weak word `weird noise`.  
2. Python hunts all three books. Sticky notes: a beep at 12:01, a laugh at 12:04, a chair scrape at 12:08.  
3. Second form: Gemma picks open ears on 12:01 (best guess from the hits).  
4. Gemma listens to a short slice and names it.  
If the books had **nothing**, we say we could not find it after the cap — we do not wander for eight rounds.

### 5. Wrong first guess — Speed 1 then 3

“When did they applaud?”  
Gemma writes `applaud`. Sound book was built around `clap`. Empty.  
Empty search **forces** Speed 3: search all three books, maybe retry query `clap` / `applause` / `hands`. The **tried** list stops us looping on `applaud` forever.

### 6. Talk + clip — Speed 2

“What did she say about pricing? Give me the clip.”

1. Form: talk + export; search talk; query `pricing`.  
2. Python: speech hits → answer from lines → ffmpeg cut around those times.  
3. User gets text + timestamp + link. Gemma never chose a tool name.

### 7. Count — Speed 1 (count stays in Python)

“How many claps?”

Search sound → merge nearby → `len()` in code. Gemma may check 2 samples.  
Stadium roar still comes back as “applause 1:00–1:40”, not “47 claps.” That is honest, not a driver bug.

### 8. A true new job — still no button

“Translate the whole talk.” “Draw a graph of every laugh.”  
Not on the form. We do **not** let 4B invent a tool. We say we cannot do that yet. A new **verb** is added on purpose later. Same honesty as before.

---

## Who does what (keep these unmixed)

| Job | Who | Why |
|---|---|---|
| Find the time | Books + `search_*` | Cheap map |
| Decide speed | **Python** | 4B should not be the manager |
| Fill the form | **E4B** | Labels, search words, pick among hits |
| Press tools, clamp FPS/windows | **Python** | Limits and order |
| Count events | **Python** `len()` | Models drop numbers |
| Understand a short slice | **E4B** on `get_frames` / `get_audio` | Eyes and ears |
| Remember “there” | **Notepad** | Context without stuffing the transcript |
| Give the user a file | `export_*` | ffmpeg |

**Find / understand / export** stay three different jobs. Same as [05-architecture.md](05-architecture.md).

---

## What we are not doing

- Dumping the whole video into Gemma  
- 12B as the default manager (optional **later**, only if hunt still fails on hard questions)  
- 32B (no audio on those Gemma sizes)  
- One frozen program per event type (clap vs bird vs laugh) — same checkboxes, different **search words**  
- Letting E4B pick raw tool names or FPS  
- An 8-round ReAct loop on 4B  

12B can still sit in a box marked “escape hatch” for a future test. v1 should not need it if hunt + notepad work.

---

## Caps (so hunt cannot become a 12B clone)

- Max **3** form-fills per question, then answer or give up.  
- Open video: short zoom (e.g. ≤8s) or a **code-owned** low-FPS skim, never `0 → 2 hours`.  
- Open audio: ≤ ~30s (Gemma’s ear limit).  
- Frame budget per question (e.g. 32–64).  
- Export max length.  
- Count in Python.  
- `tried` on the notepad: do not repeat the same search word.

---

## Where this still fails (honest)

The kitchen is the same. A smarter waiter does not create steak.

| Still fails | Why, in plain words |
|---|---|
| Tiny / quiet / too-fast event | Books sample ~1 picture/sec and 1–5s of sound. A blink can miss. |
| `$99` on a silent slide | Speech book has no eyes. Picture book finds “a slide,” it does not read the number until we **open** the frame. Hunt helps only if some hit exists. |
| Misread the slice | Right 8 seconds, Gemma still says dog vs cat. |
| True clap count in a roar | One blob, not N pops. |
| Brand-new *job* (translate all, draw a graph) | No checkbox yet. |
| “Summarize the whole 2 hours” | We never watch the whole tape. |

Hunt **does** help: wrong search word, wrong first intent, mixed questions, “what was that?”, follow-ups. Those were driver problems. This design is aimed at those.

---

## Why this can be the same 4B model

| Hard for E4B | We moved it |
|---|---|
| Long tool chains | Max 3 forms; Python runs the chain |
| Inventing tool names / FPS | Closed form + server clamps |
| Remembering the clap on turn 2 | Notepad in SQLite |
| Mixed question in one brain dump | Several intents + sorted verbs |
| Unknown question | Sticky notes from three books, then choose |
| Arithmetic on 847 claps | `len()` in Python |

What E4B still does (in-distribution): tick boxes, write a search phrase, pick among hits, look at ~8 seconds, write a short answer **given** the notepad.

---

## Suggested default (if we lock this)

| Piece | Choice |
|---|---|
| Driver | **Three speeds** on one form + one notepad |
| Brain | **Gemma 4 E4B** |
| 12B | Optional later, hunt-failed bucket only |
| Tools | Same eight; **code** calls them |
| Recipes | Speed 1 bundles (talk / look / listen / count / export / follow-up) |
| Combo | Speed 2 (many intents, one fill) |
| Unknown | Speed 3 (evidence + ≤2 extra fills) |

User-facing product does not change: upload once, ask many times, timestamps, optional clip, no 2-hour ingest into the model.

The change is **who holds the remote**: Python, with three speeds, while the small model fills a form and reads a short slice — always with the notepad in hand.
