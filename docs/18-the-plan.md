# The plan: small Gemma fills a form, Python presses the buttons

Concise write-up of the idea: **workflows + E4B**, not a 12B tool-calling waiter. Not locked yet.

---

## Plan

1. **Upload** — build three search books once: speech (WhisperX), pictures (SigLIP 2), sounds (GLAP). Optional later: slides (ColQwen / ColPali).
2. **Ask** — a **small** Gemma (E4B) fills a **short form** (intent + verbs + search words). It does **not** pick raw tools or FPS.
3. **Python** reads the form, runs the real tools (search, cut a few seconds, export), keeps a tiny **clipboard** (where we are on the timeline).
4. **Gemma again** — looks/listens to that short slice and writes the answer.

Same product as before: timestamp, optional clip, many questions on one file. Different **driver**.

## Why

A **12B** model was only there to *decide which button to press next, over and over*. Small models are bad at that. They are fine at: “this is a sound question,” “search for clap,” “yes that’s a dog.”

Code is better at order, limits, and memory. Cheaper, more predictable, still flexible — **not** a special “claps only” program.

WhisperX / ColPali are **not** chat tools. They help **build** books at upload. Verbs only **read** those books or open a short slice.

---

## Intent vs verb

**Intent** = *what kind of question?* One folder label. Does not run anything by itself.

- talk · look · listen · count · export · follow-up · not sure  

Example: “When did they clap?” → **listen**. “Give me that clip” → **export**.

**Verb** = *one allowed action.* A checkbox on the form. Each checkbox is wired in code to a tool we already designed.

| Verb (checkbox) | Python runs |
|---|---|
| search talk | `search_transcript` |
| search look | `search_visual` |
| search listen | `search_audio` |
| open eyes | `get_frames` (short slice; **code** sets FPS) |
| open ears | `get_audio` |
| shift after | move “we’re here” **forward** (“after the clap…”) |
| reuse focus | stay on the last timestamp |
| count | merge hits + `len()` in Python |
| export | `export_clip` / `export_audio` |
| not sure | search **all three** books at once |

Intent = the heading. Verbs = the steps.  
A simple question ticks one or two. A combo ticks several. That is versatility without 50 frozen recipes. The model **cannot invent** a new button.

---

## Walk-through

“After the clap, what was on the slide?”

1. Form: listen + look; verbs: search listen, shift after, open eyes; word: `clap`.
2. Python: find clap → move time forward → cut a few seconds of video.
3. Gemma reads those frames and answers.
4. Clipboard remembers that window so “was there a dog **there**?” does not search two hours.

Max two form-fills if the first search is empty. Then stop.

---

## What we are not doing

- Dumping the whole video into Gemma  
- 12B as the default manager (optional later if the form is too weak)  
- 32B (no audio on those Gemma sizes)  
- One hardcoded path per event type (clap vs bird vs laugh) — same checkboxes, different **search words**

More detail: [17-plain-map.md](17-plain-map.md) (three layers), [16-clipboard-and-verbs.md](16-clipboard-and-verbs.md) (clipboard), [15-workflows-vs-agents.md](15-workflows-vs-agents.md) (why not a free agent).

**Next proposal (not locked):** combine ready-made jobs, many intents at once, and a short hunt loop — still E4B, still a form — in [19-three-speeds.md](19-three-speeds.md).
