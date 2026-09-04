# Plain map of the whole system

Read this if the other docs feel mixed together. Three layers. They are not the same thing.

---

## Layer 1 — Phone books (built **once** per video)

These are **not** tools the chat model calls in a loop. They run at **upload**. Second question reuses them.

| Book | Model | What it stores | Tool that *reads* it later |
|---|---|---|---|
| Speech | **WhisperX** | Words + exact times | `search_transcript` |
| Pictures | **SigLIP 2** | 1 photo/sec as numbers | `search_visual` |
| Sounds | **GLAP** | 1–5s sound chunks as numbers | `search_audio` |
| Slides | **ColQwen / ColPali** | Unique slide screenshots (on-screen text) | `search_slides` |

WhisperX is not “a tool call for 12B.” It is how we **build** the speech book. ColQwen is the **fourth book** for “$99 on the slide” when nobody said the number. Human picture: [HUMAN-backend.md](../HUMAN-backend.md).

---

## Layer 2 — Tools (Python, every question)

Same eight as always. **ffmpeg** cuts. **Code** runs them (new plan) or **12B** used to pick them (old plan).

| Tool | Does |
|---|---|
| `get_meta` | Length of the file |
| `search_transcript` | Find words in the speech book |
| `search_visual` | Find “looks like a bird” |
| `search_audio` | Find “sounds like a clap” |
| `get_frames` | Open a **short** piece of video for Gemma’s eyes |
| `get_audio` | Open a **short** piece of sound for Gemma’s ears |
| `export_clip` / `export_audio` | Save a file + link |

Caps stay: no 2-hour `get_frames`. Count in Python, not in the model.

---

## Layer 3 — Brain (Gemma, question time only)

**Does not** rebuild Whisper/SigLIP. Only sees: the user question, a small **clipboard**, and whatever short slices tools just opened.

| | **Old plan (locked until we change it)** | **New plan (open)** |
|---|---|---|
| Who | Gemma **12B** | Gemma **E4B** (~4B) |
| Job | Hold the **toolbox** — pick tools, FPS, next hop | Fill a **form** (verbs) + **read** slices + **write** the answer |
| Why 12B existed | Better at long tool chains | We moved the chain into Python, so 12B is optional |
| 32B | Don’t use — those sizes have **no audio** | Same |

**Intent** is not a separate product. It is the first line of the form: “this question needs listen, then eyes.” **Verbs** are that form’s checkboxes (`search_listen`, `open_eyes`, …). Each verb maps to one or more **tools** in layer 2.

**Clipboard (context we keep):** focus time, last hits, one-line notes. **Not** the whole transcript. **Not** the movie. So follow-ups and combo questions work on a small model. See [16-clipboard-and-verbs.md](16-clipboard-and-verbs.md).

---

## Versatile, not a “claps app”

We do **not** write a special program per event. Clap, bird, price, dog, laugh — same verbs, different **search words**. New wording is still find → look/listen → answer. A brand-new *job* (e.g. translate the whole talk) = add one verb on purpose.

Cost: books once, small Gemma, short slices, cheap index searches in parallel if unsure. Scale: more videos = more books on disk, same loop.
