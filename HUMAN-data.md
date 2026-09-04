# Data + contract — for a human

This is **what we save** and **what we send**. So you know the deal between the browser, Node, and Modal.

Coding agents: still use `docs/20-backend-algorithm.md`. This page is the picture.

Times are **seconds** (64 = 1:04). IDs are short strings.

---

## Who owns what

```
Browser     only talks to Node
              │
              ▼
Laptop      SQLite  =  video, chat, sticky note, messages, clip files
            ffmpeg  =  cuts (not stored as “data”, just files)
              │
              ▼
Modal       four books  (speech / pictures / sounds / slides)
            Gemma       (does not store your chat)
```

**Rule:** the sticky note on the laptop is the clock.  
The books on Modal are the map.  
Gemma does not keep a database.

---

## How the rows connect (the family)

```
VIDEO  (one file you uploaded)
  id: vid_1
  │
  ├── CHAT  (one conversation about that file)
  │     id: chat_1
  │     │
  │     ├── STICKY NOTE  (exactly one)
  │     │     “we are at 1:04–1:12”
  │     │
  │     └── MESSAGES  (many lines)
  │           you said …  Gemma said …
  │
  └── CLIPS  (optional files we cut)
        clip_1.mp4
```

One video → many chats if you want.  
One chat → one sticky note. Always.

---

## What we save on the laptop (simple tables)

### 1. Video

“Here is the file. Are the books ready?”

| Field | Meaning | Example |
|---|---|---|
| id | name of this video | `vid_1` |
| path | where the mp4 sits | `/videos/talk.mp4` |
| duration_sec | how long | `1200` (20 min) |
| ingest_status | cooking / done / failed | `ready` |

### 2. Chat

“This thread is about that video.”

| Field | Meaning | Example |
|---|---|---|
| id | name of this chat | `chat_1` |
| video_id | points at the video | `vid_1` |

### 3. Sticky note (one per chat)

This is the **contract for memory**. If this is empty, “there” has no meaning.

| Field | Meaning | Example |
|---|---|---|
| chat_id | which chat | `chat_1` |
| video_id | which file | `vid_1` |
| focus_t0 | start of “here” | `64` |
| focus_t1 | end of “here” | `72` |
| focus_why | why we picked it | `clap` |
| hits_talk | last speech finds | `[{ t: 64, text: "…", score: 0.9 }]` |
| hits_look | last picture finds | `[{ t: 64, score: 0.7 }]` |
| hits_listen | last sound finds | `[{ t: 64, score: 0.81 }]` |
| hits_slides | last slide finds | `[{ t: 850, score: 0.88, slide_id: "s7" }]` |
| tried | searches we already did | `["listen:clap"]` |
| notes | one line Gemma wrote | `clap ~1:04; slide Q3` |
| last_user | last thing you typed | `Was there a dog there?` |
| last_answer | last thing we said | `No dog in that window.` |

**Hits** are always the same shape: **time + score** (+ text if speech, + slide_id if slides).  
That is the contract between the books and the sticky note.

### 4. Messages

The chat log. We only send Gemma the last ~8 **user** lines, not every tool.

| Field | Meaning | Example |
|---|---|---|
| chat_id | which thread | `chat_1` |
| role | who spoke | `user` or `assistant` |
| text | the words | `When did they clap?` |
| created_at | when | … |

---

## The form (not saved forever)

Gemma fills this. Node reads it once, then throws it away (or logs it for the demo).  
**Not** the source of truth. The sticky note is.

| Field | Meaning | Example |
|---|---|---|
| intents | kinds of job (can be several) | `listen`, `slides` |
| verbs | allowed steps | `search_listen`, `open_eyes` |
| queries | search words | listen=`clap`, slides=`Pro $99` |
| sure | how confident | `sure` / `mixed` / `not_sure` |
| refers_to | same place or new hunt | `focus` or `new` |

Allowed verbs (the closed list):  
`search_talk` `search_look` `search_listen` `search_slides`  
`reuse_focus` `shift_after` `open_eyes` `open_ears`  
`count_hits` `export` `unsure`

If Gemma writes a verb not on this list, Node ignores it. That is the contract.

---

## What the browser and Node promise each other

### You upload

**You → Node:** the mp4 file.

**Node → you:**

```
id: vid_1
status: processing    (later: ready)
```

When `ready`, you may chat. If `error`, ingest failed.

### You ask

**You → Node:**

```
video: vid_1
chat:  chat_1
text:  "When did they clap?"
```

While it works, Node **streams status** (spinner text):

```
searching sound…
cutting 8 seconds…
Gemma reading…
```

**Node → you (final):**

```
text:         "They clapped at 1:04."
timestamps:   [64]
quotes:       [{ t: 64, text: "…", speaker: "SPEAKER_1" }]   // if talk
frames:       ["http://localhost/.../frame_64.jpg"]         // what Gemma saw
export_url:   null
status_done:  true
```

If nothing: `text` = we couldn’t find it; quotes/frames may be empty.

Refresh the page: this chat is **gone**.

---

## What Node and Modal promise each other

Books live on Modal. Node never “has” the vectors. It only asks.

### Build books (once)

**Node → Modal:** video id + the file (or a path).

**Modal → Node:** `ok` when all four books exist.

### Search a book

**Node → Modal:**

```
video: vid_1
query: "clap"
```

**Modal → Node:** a list of hits (same shape every book):

```
[ { t: 64, score: 0.81 } ]
```

Speech may add `text`. Slides may add `slide_id`.  
If nothing: `[]`. Empty list is how Door 3 (hunt) starts.

Four doors on Modal, same hit contract:

- search talk  
- search look  
- search listen  
- search slides  

### Fill the form (main Gemma)

**Node → Modal:**

```
question:     "Was there a dog there?"
user_history: ["When did they clap?", "Was there a dog there?"]
notepad:      { focus 64–72, last_answer, tried, hits… }
duration:     1200
```

**Modal → Node:** the **form** (table above).

Chat = your words. Notepad = the clock. Both go in. That is the memory contract.

### Write the answer (answer Gemma)

**Node → Modal:**

```
question + user_history + notepad
frames:  a few photos Node just cut   (or none)
audio:   a short wav                  (or none)
```

**Modal → Node:**

```
text: "No dog in that window."
```

Node then stamps **timestamps from the sticky note**, not from Gemma guessing a new clock.  
If Gemma says a time we never searched, we don’t trust it. Sticky note wins.

---

## One question, data moving

You: “When did they clap?”

```
1. Browser → Node
     text = that sentence
     Node appends a MESSAGE (role=user)

2. Node → Modal  (plan)
     history + empty-ish sticky note
     ← form: listen, search_listen, query clap

3. Node → Modal  (search listen)
     query clap
     ← [{ t: 64, score: 0.81 }]

4. Node writes STICKY NOTE
     focus 64–72
     hits_listen = that hit
     tried = listen:clap

5. Node → Modal  (answer)
     notepad + maybe 2 sec of sound
     ← "They clapped at 1:04."

6. Node → Browser
     text + timestamps [64]
     Node appends a MESSAGE (role=assistant)
     last_answer saved on the sticky note
```

Next: “Was there a dog **there**?”  
Step 2 now includes history + focus 64–72.  
Node does **not** search 20 minutes. It opens 64–72.

---

## Tiny dictionary

| Word | What it is |
|---|---|
| **id** | a name so rows can point at each other |
| **t / focus** | a time on the video, in seconds |
| **hit** | “something matched at this time, this strongly” |
| **form** | Gemma’s checklist for this turn (throwaway) |
| **sticky note** | saved memory for the chat (kept) |
| **contract** | “if you send me this shape, I send you that shape” |

---

## Super short

Laptop session (gone on refresh): **video pointer, chat, sticky note, messages**.  
Video file: **on your disk**.  
Modal: **four books**.  
Browser sees: **status, text, times, transcript quote, frames, optional clip**.  
Every search returns **time + score**.  
Gemma in: **your last lines + sticky note**.  
Gemma out: **form**, then later **answer text**.  
The clock always lives on the sticky note.
