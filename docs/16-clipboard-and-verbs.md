# Clipboard + verb menu (small model, not a rigid recipe)

How we fix combo questions, wrong intent, and “a 9th kind of question” **without** a 12B free agent.

The bet: **Python keeps a clipboard (state).** Gemma E4B only ticks a **short menu** of verbs. Code runs the verbs, writes results back on the clipboard, then Gemma answers from that. Not one frozen recipe. Not an open toolbox. **Enough structure for a small model.**

This is Google’s `handle_id` + `step_list`, Anthropic’s routing + a **bounded** loop, and our existing “session remembers last times” — made explicit.

---

## Why one recipe breaks

| Failure | What happens with a single `intent=` |
|---|---|
| Combo | “After the clap, what was on the slide, and was there a dog?” needs listen → move time forward → eyes → maybe a second look |
| Wrong intent | One mis-label and we search the wrong book |
| New wording | “What changed on screen when they laughed?” is still find + look, but it doesn’t match a named workflow |

A 12B agent would improvise tools. A 4B model improvising tools is how you get garbage FPS and extra rounds. So we **do not** give it tools. We give it a **menu** and a **clipboard**.

---

## The clipboard (we own this)

One SQLite row per chat (plus the video `handle_id`). Compact. **Not** the video. **Not** every frame.

```
video_id, duration
focus: { t0, t1, why }          # “the place we’re talking about”
hits:
  transcript: [{ t, text }]     # last search
  visual:     [{ t, score }]
  audio:      [{ t, score }]
notes: "clap ~1:04; slide still up"   # one-line memory Gemma wrote
last_user, last_answer
```

Every turn we send Gemma: the new question + **this clipboard** (a few hundred tokens). Follow-up “was there a dog **in that frame**?” is `reuse focus` — we already knew this product needed it.

Code updates the clipboard after every verb. The model does not have to remember across calls. **State lives in the database.**

---

## The verb menu (closed list)

Not eight free tool calls. A JSON enum the server **grammar-constrains** (xgrammar / outlines). E4B is good at filling a form. It is bad at inventing a form.

| Verb | What code actually does |
|---|---|
| `reuse_focus` | Keep `focus`; don’t search the whole tape |
| `search_talk` | FTS / WhisperX with `queries.talk` |
| `search_look` | SigLIP (`queries.look`) |
| `search_listen` | GLAP (`queries.listen`) |
| `search_slides` | ColQwen on unique slides, if we built that index |
| `shift_after` | Set focus to *after* the best current hit (combo: clap → then) |
| `open_eyes` | `get_frames` on **focus**, caps on window/FPS |
| `open_ears` | `get_audio` on **focus**, ≤30s |
| `count_hits` | Merge + `len()` in Python |
| `export` | ffmpeg on focus, duration cap |
| `unsure` | Code runs **talk + look + listen** searches in **parallel** (indexes are ms) |
| `done` | Stop planning; go to the answer call |

Gemma may tick **several verbs in one shot**. That is how combo questions glue together. Code **sorts** them (search before open, `shift_after` after the search it depends on). The model never picks FPS or a 2-hour window — the runtime clamps.

Example plan for the scary sentence:

```
verbs: [search_listen, shift_after, open_eyes, search_look]
queries: { listen: "clap", look: "dog" }
```

Code: find clap → move focus to the next few seconds → open frames (slide) → also picture-search “dog” near focus → write hits onto the clipboard → **second** Gemma call: read frames + hits → one answer.

---

## The loop (bounded — this is the whole “agent”)

```
1. Plan     E4B → JSON verbs   (sees question + clipboard)
2. Act      Python runs verbs, updates clipboard
3. Maybe    if hits empty or Gemma set unsure:
            one more Plan (max 2 plans total)
4. Answer   E4B reads clipboard + opened frames/audio → text
```

Two plans, not eight. If still empty, say we couldn’t find it — don’t wander.

**Wrong intent:** Gemma sets `unsure`, **or** the first search returns nothing. Code does the parallel triple-search (`unsure` verb). The second plan is easy: “here are hits in all three books; pick focus and open_eyes/ears.” Small models can choose among **evidence**. They struggle when they must **imagine** evidence.

**9th question type:** if it is still “find a time, look or listen, speak,” the menu already covers it. New *wording* is not a new workflow. A true new *job* (translate the whole talk, draw a graph) is a new **verb** we add on purpose. That honesty stays.

---

## Why the small model is enough here

| Hard for E4B | We removed it |
|---|---|
| Long tool chains | Max 2 JSON plans |
| Inventing tool names / FPS | Closed enum + server clamps |
| Remembering the clap time on turn 2 | Clipboard in SQLite |
| Multi-hop in one brain dump | Several verbs + `shift_after` in code |
| Arithmetic on events | `count_hits` in Python |

What E4B still does well: tick boxes, write a search phrase, look at 8 seconds of slides, write a short answer **given** the clipboard.

---

## Session rules

1. Clipboard is **source of truth**. Don’t stuff the full transcript into Gemma.
2. `focus` is one window. Combo questions update it in order (`shift_after`).
3. Follow-ups default to `reuse_focus` unless the user names a new thing.
4. Parallel search is cheap; parallel **Gemma gulps** are not — still cap frames.
5. Same product: timestamps, optional export, no 2h ingest into the model.

This is the driver to lock if we want workflows **and** combo questions: **clipboard + verb menu + two-plan cap**, not a named recipe per question and not a 12B waiter.
