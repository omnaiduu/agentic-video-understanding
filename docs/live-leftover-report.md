# Report: leftover live issues — problems, what we found, how we fixed them

This is a written report of the leftover exam-tape work. Plain language first. Not an answer key for this video. Gemma still chooses look / listen / spoken words / printed slides / sounds. The laptop only adds rules about **how those books work**. We did not hardcode “beep → 11s”, “claps → 0”, or “printed number → gold”.

PR: [Look at the middle of a sound hit and the next unused slide](https://github.com/omnaiduu/agentic-video-understanding/pull/26) (`feature/loop-next-hit-b374`).

---

## What the tape actually is

A 16-second file, on purpose messy:

| Time | On screen | Sound |
|---|---|---|
| 0–6s | Navy **Pricing**, gold/yellow **$99** | Someone **says** “$99 a month” |
| 6–10s | **RED ALERT** | Silence |
| 10–16s | **Q3 / Ship the slide index** (never spoken) | A tone around **11s** |

Speech, print, and sound disagree. That is the exam.

Gemma does not get the whole video. Each turn it picks one **move**. We allow **12 moves**, then we force an answer. One look may attach at most **12 photos**.

---

## The problems

Four questions still failed after the earlier “spoken words, then stop” notes.

### 1. Walk the whole tape (H8)

**Ask:** go through the video in order, including things nobody said out loud.

**Should:** Pricing / $99, then RED ALERT, then Q3 and the beep.

**Problem:** Gemma walked **two seconds at a time** (look, then listen). Each pair costs two of 12 moves. By ~9s the loop said “answer now.” Q3 (10s+) was never opened. It *was* walking. The **move budget** ran out first.

### 2. Clip when the beep happens (H7)

**Ask:** make a short clip of whatever is on screen when the beep happens.

**Should:** a tight cut around ~11s (Q3 + the tone), not the red slide.

**Problem:** sound search does not return “beep at 11.00s.” It returns a **window**, often **9–12s**. The beep sits near the **middle**. The **start** of that window is still RED ALERT. Gemma exported the whole window. Result: red **and** Q3.

### 3. Printed number color vs speech (M1)

**Ask:** they said a number is also printed on the slide. What color is it, and does it match what they said?

**Should:** gold/yellow **$99** on Pricing; speech also says $99, so they match.

**Problem:** Gemma **did** look at Pricing and could see yellow $99. It never opened **spoken words**, then said it could not tell if that matched speech. The spoken $99 was sitting in the transcript the whole time.

### 4. How many claps? (H5)

**Ask:** how many claps are in this recording?

**Should:** **zero.** This tape has speech, silence, and a tone. No claps.

**Problem:** sound search is **not** a clap detector. It returns times that are *somewhat like* the query (false neighbors). Gemma treated those rows as a count, or listened to silence and still said “one clap.”

---

## What we found (live Modal Gemma)

We ran the same eight hidden-intent questions against **Gemma 4 E4B on Modal**, FastAPI on this machine, fresh chat per question. We do **not** call pass without HTTP **200**.

Tape upload: `c1d9beb7-5465-4f47-9d53-2d6b299104b5`.

### Before these leftover rules

- **H8** — crawled 2s steps; never reached Q3.
- **H7** — exported the whole 9–12s sound window (red + Q3).
- **M1** — named yellow $99, then hedged on speech (never searched it).
- **H5** — invented claps, or said it could not count.

Easy checks still worked: **E1** ($99), **M3** (ship the slide index), **M4** (tone + Q3 on screen).

### After skip-ahead and centered recut (first leftover PR)

- **H8 pass** — skip blocked 2–4s; named Pricing, RED ALERT, Q3.
- **H7 leftover pass** — sometimes exported 11.5–14.5 on its own; sometimes recut 9–12 → **9.5–11.5** (still ~0.5s of red).
- **M1 still partial** — yellow $99; never searched speech.
- **H5 still fail** — listened to silence, answered **one clap**. Notes did not stick.

### After speech-match bounce, count bounce, recut-from-middle, look-only skip

**Final live rerun** (all HTTP 200):

| Q | What happened | Verdict |
|---|---|---|
| **E1** How much does Pro cost? | Speech. “$99 a month.” | **Pass** |
| **H1** Is $99 on the red screen? | Looked at 0s, 6s, and 10s. Found $99 at 0s. Led with “Yes” (the trap). | **Partial** |
| **M3** What do we ship this quarter? | Speech → slides → look 10s. “Ship the slide index.” | **Pass** |
| **M4** When is the tone, what’s on screen? | Sound 9–12 → look+listen **10.5–12.5**. Q3. | **Pass** |
| **H8** Walk the whole tape | look+listen 0–2, **skip 2–4**, then RED ALERT and Q3. | **Pass** |
| **H7** Clip on the beep | Export **9–12** → recut **10.5–12.5**. Q3 + beep, not red. | **Pass** |
| **M1** Printed number color + match? | Looks 10, **0**, 6, then **search speech**. Yellow 99 matches spoken $99. | **Pass** |
| **H5** How many claps? | Listen 7.5–9.5. “Cannot definitively count.” | **Partial** — no invented “one clap”; still not **zero** |

A middle live run also showed two extra holes we then closed:

- **Look-only crawl (H8):** without a matching listen, it took 1.5s looks for 12 moves and never wrote a real walkthrough. **Fix:** skip that crawl too when more than 6s remain.
- **Export spam (H7):** a decent 11.5–14.5 clip, then it kept exporting later and later until **15.5–16s** (end silence). **Fix:** after a clip that is **not** the whole search window, block further exports and ask it to answer with the URL.

---

## How we fixed it

Laptop rules only. No new architecture. No React. No keyword list for this tape.

### H8 — skip ahead

If the last look ended at time T, the next look or listen starts at ~T (a 2s step), and more than **6s** of video remain, **block** that move: “you already did that beat — look several seconds later.”

First version required a matching listen. Live then showed a **look-only** crawl. We skip that too. Tiny 1s test files never fire (not enough tape left). We did **not** raise the 12-move cap.

### H7 — recut from the middle, then stop

1. Remember sound-hit `[start, end]`.
2. If the export is that whole window (or near it, e.g. 9.75–12.75 vs 9–12), nudge: recut **from the middle forward** ~2s, not before the middle. A 9–12 hit becomes ~**10.5–12.5**.
3. Bounce answers until that recut exists.
4. If it already exported a **short** clip, **do not export again** (stops walking off the end of the file).

Centered ±1s had left ~0.5s of red. Starting at the middle drops the previous slide.

### M1 — force spoken words before “does it match”

1. After a slide look: if you see a price or digits, that **is** the printed number — name the color.
2. If the question talks about something **printed** *and* **what they said**, **refuse the answer** until it searches spoken words.
3. After that search: those lines are what was said; if a line names a number, that is the spoken value; say whether it matches the pixels.

We do not OCR the JPEG. We do not hardcode “gold” or “$99”.

### H5 — hits are not a count; default zero

1. On a “how many …” question that used sound search: **no answer until it listens**.
2. After listen: bounce the first **two** answers. Hit rows are not the count. Speech, silence, or a different tone is **zero**. If unsure, the answer is **zero**.
3. Stronger listen note: this window is zero unless you clearly heard that exact sound.

There is still **no clap detector**. We cannot read the WAV and reject a wrong count without guessing. Live: it stopped saying “one clap”; it still will not reliably say **zero**.

---

## What else we did

- **Unit tests** on black 12s / 1s files, not this exam tape: skip-ahead (with and without listen), recut from the middle, near-full windows still count as the hit, extra export blocked, print-vs-speech bounce, how-many listen bounce. Laptop notes still do not contain beep / clap / ship / $99.
- **Live Modal reruns** of the eight questions, more than once, after each rule change. FastAPI restarted so it loaded new loop code. Gemma cold-started on Modal when `/v1/models` returned 503.
- **Docs:** this report, plus the issue/solution card in [four leftover live issues](live-leftover-issues.md), indexed from [docs/README](README.md).
- **Did not** add a Notion task, a new database, a new UI, or a clap/OCR model.

Code that changed: `backend/app/agent/loop.py`, `parts.py`, `schema.py`, and tests in `test_loop_rules.py`, `test_chat.py`, `test_audio.py`.

---

## What is still open

| Item | Status |
|---|---|
| Skip in the last 6 seconds of a file | By design (lets a short file finish). |
| H5 saying the word **zero** | Unstable without a sound classifier. |
| H1 trap (“confirm $99 is on red”) | Sometimes leads with “Yes” even after looking at Pricing. |
| Color word gold vs yellow | Gemma’s wording. We do not OCR. |
| Beep mentioned in the H8 sentence | Walk names the three slides; the tone is not always in the final text. |

A list of words for *this* video would pass the exam and fail the next file. That is not a fix.

---

## Bottom line

The leftover set was: walk the tape, clip the beep, name the printed color and match speech, count claps.

On live Modal Gemma, **walk, beep clip, and printed-number match now pass** with HTTP 200. **Clap count** no longer invents “one clap” and still will not say **zero**. That last one needs a real detector, not another note.
