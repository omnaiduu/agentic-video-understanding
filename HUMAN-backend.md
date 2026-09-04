# The backend — for a human (not for coding agents)

This page is **for you**. It is the whole picture in plain language.

Coding agents should use `docs/20-backend-algorithm.md` and the other numbered docs. You do not need those.

---

## The whole building

Imagine two rooms.

```
 YOU  (browser)
   │
   │  type a question, see the answer, click a timestamp, download a clip
   ▼
 ┌─────────────────────────────────────────┐
 │  YOUR LAPTOP  —  Node                   │
 │                                         │
 │  • takes the question                   │
 │  • keeps a sticky note (“we are at 1:04”)│
 │  • decides the path                     │
 │  • cuts a few seconds with ffmpeg       │
 │  • never watches the whole movie        │
 └──────────────┬──────────────────────────┘
                │  “search this word”
                │  “fill this form”
                │  “look at these 8 photos”
                ▼
 ┌─────────────────────────────────────────┐
 │  MODAL.COM  —  the models (Python/GPU)  │
 │                                         │
 │  Four books (built once at upload):     │
 │    speech    WhisperX                   │
 │    pictures  SigLIP                     │
 │    sounds    GLAP                       │
 │    slides    ColQwen / ColPali          │
 │                                         │
 │  Brain: small Gemma                     │
 │    1) fill a form                       │
 │    2) look at a short slice and answer  │
 └─────────────────────────────────────────┘
```

**Node is the hands and the memory.**  
**Modal is the eyes, ears, and the four books.**  
**Gemma never holds the remote.** It only fills a form, then looks at a few seconds Node already cut.

---

## Two different days

### Day 1 — you upload a video (once)

The file is saved. Modal builds **four books**. This can take a while. After that, the books sit on the shelf.

Question 2, 3, 4… **do not rebuild the books.**

### Day 2 — you ask questions (many times)

Fast. We only:

1. look in a book (find a time)  
2. cut a few seconds  
3. let Gemma look/listen to **that** bit  
4. answer, with a timestamp, maybe a clip

We never dump two hours into Gemma.

---

## The four books (this is the map of the video)

Think of the back of a textbook: you look up a word, you get a **page number**. The book does not write your essay. Gemma writes the essay after we open that page.

| Book | Built by | You are looking up | Example hit |
|---|---|---|---|
| **Speech** | WhisperX | words people **said** | `pricing` → 12:04, she said “let’s talk price” |
| **Pictures** | SigLIP | what a moment **looks like** | `red bird` → 3:22 |
| **Sounds** | GLAP | what a moment **sounds like** | `clap` → 1:04 |
| **Slides** | **ColQwen** (or ColPali if ColQwen is a pain) | **text printed on screen**, even if nobody said it | `Pro $99` → slide that was up 14:10–14:40 |

### Why a fourth book? (the part that was missing)

The picture book sees **a slide**. It does not read **$99**.  
The speech book only hears the mic. If she never said “ninety-nine,” speech is empty.  
Gemma **can** read $99 — but only if we already know **which second** to open.

So ColQwen is the **finder for writing on slides**.

```
“Which slide had Pro $99?”  (she never said the number)

  speech book     ✗  nobody said it
  picture book    ✗  every slide “looks like a slide”
  sound book      ✗  not a sound
  slide book      ✓  ColQwen: that page has “$99”  →  14:10

  Node cuts a few frames at 14:10
  Gemma reads: “It says Pro $99.”
```

ColQwen does **not** answer. It only points at a time. Same as the other books.

We do **not** run ColQwen on every second. At upload we first **collapse copies** of the same slide (one slide on screen for a minute is not 60 different pages). ColQwen only sees those **unique** slides. Cheap.

---

## Two memories (so “there” works)

| | Lives in | Example |
|---|---|---|
| **Chat** | last things **you** typed | “Was there a dog **there**?” |
| **Sticky note** | a small save on the laptop | we are at **1:04–1:12**, last find was a clap |

You never type “1:04.” Search found it. Node wrote it down.

- Chat = what you **mean**  
- Sticky note = **where** in the video  

Gemma gets both when it fills the form. Chat alone cannot fill the clock.

---

## The logic, in one breath

```
you ask
   → Gemma reads chat + sticky note
   → Gemma ticks boxes on a short form
        (talk? look? listen? slides? count? save clip?
         search words? same place or new place?)
   → Node reads the form and picks a door
   → Node searches books / cuts a clip / counts
   → Node updates the sticky note
   → Gemma looks at a few seconds
   → you get text + time + maybe a file
```

Three doors Node can pick:

```
        form comes back
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
  Door 1    Door 2    Door 3
  Easy      Mix       Hunt
  one job   several   we don’t know
              │         or empty
              ▼
         short look
              ▼
           answer
```

**Door 1 — easy.** “When did they clap?” Search sounds. Done.  
**Door 2 — mix.** “After the clap, what was on the slide?” Find clap, move forward, open eyes.  
**Door 3 — hunt.** “What was that noise?” or first search empty. Search **all four books**, put hits on the table, Gemma picks which one to open. Try a little, then stop.

Gemma does **not** pick the door. Node does.

---

## A question, like a comic strip

**You type:** After the clap, what was on the slide? Was it the Pro $99 one?

```
[1] Node
    loads sticky note (maybe empty)
    loads last things you said

[2] Gemma (main) — only text, no video
    “this is listen + slides”
    “search clap, then look for Pro $99”
    “not a brand new topic”

[3] Node — Door 2 (mix)
    sound book: clap at 1:04
    sticky note: we are at 1:04
    move a few seconds forward
    slide book: “Pro $99” also lives around 1:10
    ffmpeg: cut ~8 photos from that window

[4] Gemma (answer) — sees those photos
    “Yes. Right after the clap, the slide says Pro $99.”

[5] You
    see 1:04 and 1:10 as clickable times
```

Next line from you: **“Give me that clip.”**  
Door 1. Node already knows the window. ffmpeg saves a file. Link.

Next line: **“Was there a dog there?”**  
“There” = chat. **1:04** = sticky note. Node does **not** scan the whole tape.

---

## Hunt, simply

First try failed, or you were vague.

```
search speech + pictures + sounds + slides   (all at once, cheap)
        │
        ▼
  sticky notes on the table
    12:01 beep
    12:04 laugh
    14:10 a slide with $99
        │
        ▼
  Gemma picks: “open ears on 12:01”
        │
        ▼
  Node cuts that sound
  Gemma names it
```

If the table is empty, we say we couldn’t find it. We do **not** watch two hours. We do **not** loop forever.

Wrong word is the same door: you said “applaud,” the book knows “clap,” first search empty, hunt finds clap anyway.

---

## Who does what (so jobs don’t mix)

| Job | Who | Not who |
|---|---|---|
| Find the time | the four books | Gemma guessing |
| Decide the path | Node | small Gemma |
| Count claps | Node (just count the hits) | Gemma’s head |
| Read the slide / confirm the dog | Gemma, on a **short** cut | the books (they only point) |
| Remember “there” | sticky note | hoping the model remembers |
| Save a clip | ffmpeg | Gemma |

Find. Then understand. Then maybe export. Three jobs. Don’t mash them.

---

## What you see vs what is hidden

**You see:** a page with the video, a chat box, times you can click, a download link.

**Hidden on the laptop:** Node, the sticky note, ffmpeg, the mp4.

**Hidden on Modal:** the four books, Gemma.

You never pick a model. You never pick FPS. You never see “tool call 7.” For a demo we can show a tiny trace (“searched sound → opened eyes”) if you want to film it.

---

## What this will not do

- Invent 1:04 from your words alone (the sticky note must hold it).  
- Read $99 if we never open that frame (ColQwen only **finds** the second).  
- Count 47 claps inside one stadium roar (that is one blob).  
- Translate the whole talk or draw a graph (no button for that yet).  
- Catch a mosquito on the lens for 0.2 seconds if no book stored it.

---

## Super short

Four books, including **slides** (ColQwen/ColPali) for writing nobody said.  
Node on your laptop. Models on Modal.  
Gemma fills a form from **chat + sticky note**, then reads a few seconds.  
Easy door, mix door, hunt door.  
Upload once. Ask many times. Timestamp. Optional clip.

That is the whole backend.

---

## Data / contract

What we save and what we send: **[HUMAN-data.md](HUMAN-data.md)**.  
What you locked: **[HUMAN-locked.md](HUMAN-locked.md)**.

