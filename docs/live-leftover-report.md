# Report: leftover live issues — problems, what we found, how we fixed them

This is the long write-up. Same facts as [four leftover live issues](live-leftover-issues.md), told with more of the “why”.

Not an answer key. Gemma still chooses look / listen / spoken words / printed slides / sounds. The laptop only adds rules about **how those books work**. We did not hardcode “beep → 11s”, “claps → 0”, or “printed number → gold”. That would pass *this* tape and fail the next file.

PR: [Look at the middle of a sound hit and the next unused slide](https://github.com/omnaiduu/agentic-video-understanding/pull/26) (`feature/loop-next-hit-b374`).

---

## How this machine actually works

There are two brains.

**Gemma** (on Modal, GPU) never sees the whole video. Each turn it fills a JSON form: look, listen, search spoken words, search pictures, search sounds, search printed slides, export a clip, or answer. It does not call tools. It only picks a move and times.

**The laptop** (this FastAPI process) runs that move. It cuts JPEGs, cuts a wav, searches Postgres indexes, or writes an mp4. Then it sends a **normal user message** back: “frames at 0.00s”, or “transcript hits…”, or “that cut was the whole search window”. Gemma’s next JSON is based on that note plus whatever photos or one wav we attached.

That back-and-forth is the **loop**. We allow **12 moves**, then we force an answer. One look may attach at most **12 photos**. Gemma’s prompt is small (~8k). Dumping the whole 16s (or a two-hour file) as pictures would blow it up. So the leftover bugs are not “Gemma is dumb.” They are “the loop ran out of moves,” or “the book returned a *window*, not a pin,” or “Gemma answered before opening the other book.”

The **books**:

| Book | What it actually is | What it is *not* |
|---|---|---|
| Spoken words (`search`) | Whisper lines + meaning search | The printed slides |
| Pictures (`search_visual`) | SigLIP “what does this look like” | Reading slide text |
| Printed slides (`search_slides`) | ColQwen “which unique slide” | A guarantee it ranked Pricing first |
| Sounds (`search_audio`) | CLAP “windows that *sound like* the query” | A clap counter, or “beep at 11.00s” |

---

## What the tape actually is

A 16-second file, messy on purpose. Speech, print, and sound **disagree**.

| Time | On screen | Sound |
|---|---|---|
| 0–6s | Navy **Pricing**, gold/yellow **Pro $99** | “The pro plan is $99 a month.” Then “The number is also printed on the slide.” |
| 6–10s | Solid **RED ALERT** | Silence |
| 10–16s | Dark green **Q3 Roadmap / Ship the slide index** | A tone ~**11.0–11.75s**, then quiet |

Nobody ever *says* “ship the slide index” or “Q3”. That text exists only as pixels. The beep is a tone, not a spoken word. There are **no claps**.

Upload used for the live reruns: `c1d9beb7-5465-4f47-9d53-2d6b299104b5`. Gemma 4 E4B on Modal. Fresh chat session per question. We do **not** call pass without HTTP **200**.

---

## The four leftover problems

These are what was still wrong after [spoken words, then stop](live-spoken-words.md). That earlier fix stopped Gemma from searching speech twice and quitting. It did **not** fix walking, recutting, matching print to speech, or clap count.

### 1. Walk the whole tape (H8)

**Ask:** “Walk through the whole tape in order, including things nobody said out loud.”

**Should:** Pricing / $99, then RED ALERT, then Q3 and (ideally) the beep.

**What went wrong.** Gemma started at 0s and took **two-second** looks and listens: 0–2, then 2–4, then 4–6… Each look *or* listen costs one of 12 moves. Two moves cover two seconds of tape. By ~9s the loop said “answer now.” Q3 (10s+) was never opened.

This is easy to misread as “it refused to walk.” It *was* walking, in tiny steps. The **move budget** ran out first. The slide book already knew 10s. This question never jumped there.

Raising 12 rounds would only attach more photos and still crawl. The fix is to **stop the crawl** when a lot of file is still left.

### 2. Clip when the beep happens (H7)

**Ask:** “Make a three-second clip of whatever is on screen when the beep happens.”

**Should:** a tight cut around ~11s (Q3 + the tone), not the red slide.

**What went wrong.** Sound search is CLAP. It does not return “beep at 11.00s.” It returns a **window of audio that is similar to the query**, often **9–12s**. The beep sits near the **middle** (~10.5s). The **start** of that window (9s) is still RED ALERT. Gemma exported 9–12 because that is the hit it was given. The laptop cut *exactly* those times. Result: red **and** Q3, beep somewhere inside.

A second version of the same bug: it exported a *near* window (9.75–12.75) so a tight “equals 9–12” check never fired. A third version: a decent 11.5–14.5 clip, then it kept exporting later and later until **15.5–16s** (end silence) and burned all 12 moves.

### 3. Printed number color vs speech (M1)

**Ask:** “They said a number is also printed on the slide. What color is that number, and does it match what they said?”

**Should:** gold/yellow **$99** on Pricing; speech also says $99, so they match.

**What went wrong, in two layers.**

Earlier: ColQwen ranked “number printed on the slide” as **Q3, then Pricing, then red**. Gemma looked at Q3 (no number), skipped Pricing, looked at red. Answer: cannot confirm a printed number. We already had “look at the next unused slide time” for that.

Later, after that walk-the-list rule: it **did** look at 0s. The photo **does** show yellow $99. Then it answered without opening spoken words: “no spoken number was heard, cannot confirm a match.” The spoken $99 was in Whisper at 0s the whole time. It never searched speech, so it honestly thought there was nothing to compare.

Hedging (“might be gold”) was a third layer. We cannot OCR the JPEG or force the word “gold” without hardcoding this tape. Yellow vs gold is Gemma’s wording.

### 4. How many claps? (H5)

**Ask:** “How many claps are in this recording?”

**Should:** **zero.**

**What went wrong.** Sound search is not a clap detector. It finds chunks *somewhat like* “clap.” False neighbors still get **times**. Gemma then:

- treated the **number of rows** as the count (“there are eight hits, so eight claps”), or
- listened to **silence** at 7.5–9s (the red slide) and said it “clearly heard one clap,” or
- listened and said it cannot count.

The laptop never counts claps in the WAV. A note that says “if unsure, zero” is only a note. Gemma can ignore it. Forcing the answer to contain the word “zero” would pass this tape and fail “how many beeps?” (answer: one).

---

## What we found on live Gemma (the actual runs)

Same eight questions each time. Not the full 19-question suite — the leftover four plus the easy checks so we did not break $99 / ship / tone.

### Run A — after skip-ahead + centered recut, before speech bounce

H8 skip **did** fire: look+listen 0–2, blocked 2–4 (`skip ahead`), then 6s / 10s / 14s. Named Pricing $99, RED ALERT, Q3. **Pass** (beep not always in the sentence).

H7: one run exported **11.5–14.5** without needing the nudge (Q3, leftover pass). Another exported 9–12 then recut **9.5–11.5** (centered on 10.5). That still included ~0.5s of red, and it cut off the tone after 11.5s.

M1: yellow $99; “cannot confirm it matches speech.” Never called `search`. **Partial.**

H5: listen 7.5–9, answered **one clap**. **Fail.**

E1 / H1 / M3 / M4 passed on that run.

### Run B — after speech bounce + count bounce, before look-only skip

M1 **passed**: looked 10, 0, 6, then `search` at 3.12s *and* 0s. “Yellow 99 matches spoken $99.”

H5: “I have not clearly heard any claps” (good) on one run; later “cannot definitively count” (not the word zero). **Partial.**

H7 **failed** that run: first clip 11.5–14.5 was fine, then it exported 13.5–15.5, 14.5–16, 15.5–16… until the forced dump. Recut nudge never fired because 11.5–14.5 was *not* the 9–12 window.

H8 **failed** that run: **look-only** 1.5s steps, 0–1.5, 1.5–3, … 14.5–16. No matching listen, so skip-ahead did not fire. Twelve looks, then a dump of step names, not a walkthrough. This was the known unit-test hole showing up live.

### Run C — final, after look-only skip + extra-export cap

All eight HTTP **200**.

| Q | What Gemma actually did | Verdict |
|---|---|---|
| **E1** How much does Pro cost? | `search` only. “$99 a month.” | **Pass** |
| **H1** Is $99 on the red screen? | Looks 0, 6, 10. Finds $99 at 0s. Leads with “Yes” (the trap). | **Partial** |
| **M3** What do we ship this quarter? | Speech → slides → look 10s. “Ship the slide index.” | **Pass** |
| **M4** When is the tone, what’s on screen? | Sound 9–12 → look+listen **10.5–12.5**. Q3. | **Pass** |
| **H8** Walk the tape | look+listen 0–2, **skip 2–4**, then 8–10 (RED ALERT), 12–16 (Q3). Names Pricing $99, Red Alert, Q3. | **Pass** |
| **H7** Clip on the beep | Export **9–12** → recut **10.5–12.5**. Q3 + beep, not red. | **Pass** |
| **M1** Printed number + match? | Looks 10, **0**, 6, then **search speech**. Yellow 99 matches spoken $99. | **Pass** |
| **H5** How many claps? | Listen 7.5–9.5. “Cannot definitively count.” | **Partial** |

---

## How we fixed it (laptop rules, in order)

A **bounce** means: Gemma sent `do: answer`. The laptop **does not accept it**. It appends a user note, counts a round so we cannot loop forever, and asks again. The refused sentence never becomes the API answer.

### H8 — skip ahead

**Rule.** Last look ended at time T. Next look or listen starts at ~T (a ~2s step). More than **6s** of video remain. Block that move. Message: you already looked at that beat; look several seconds later; the file goes until 16s.

**Why 6s.** A 1s test file would otherwise skip and never finish. Remaining ≤ 6 → crawl is allowed. Remaining > 6 → skip. We did **not** raise 12 rounds.

**Look-only.** First version required a matching listen (so look 0–2 + listen 0–2, then look 2–4 is blocked). Live Gemma sometimes never listened and crawled 1.5s looks. Same rule now fires with **no** listen. If look and listen were *different* windows (look 0–2, listen 6–8), we still do **not** skip — that is not a crawl.

**What we did not do.** We did not say “if they ask to walk the tape, jump to 0, 6, and 10.” That is this file’s slide times.

### H7 — recut from the middle, then stop

**Rule 1.** Remember each sound-hit `[start, end]`. If `export_clip` matches that window within **1s** on both ends (so 9.75–12.75 still counts as 9–12), treat it as the whole hit.

**Rule 2.** Nudge: recut **from the middle forward** ~2s, not before the middle. Middle of 9–12 is 10.5 → ask for ~**10.5–12.5** (capped at file end). Bounce answers until that recut exists.

**Why not ±1s.** Centered 9.5–11.5 still included 9.5–10 (red) and chopped the tone after 11.5. The start of a search window is often the **previous slide**. Starting at the middle drops it.

**Rule 3.** After a clip that is **not** the whole search window, block further exports: you already have a cut; answer with the URL. That stopped the 15.5–16 death spiral.

**What we did not do.** We did not say “if they say beep, export 10.5–12.5.”

### M1 — force spoken words before “does it match”

**Rule 1.** After a slide look: if you see a price or digits, that **is** the printed number — name the color. Unused slide times stay listed so Pricing is not skipped.

**Rule 2.** If the question talks about something **printed** *and* **what they said**, refuse `answer` until `search` (spoken words) has run.

**Rule 3.** After that search: those lines are what was said. If a line names a number or price, that is the spoken value. Compare it to the printed digits. Say whether they match.

Live, search returned both 3.12s (“the number is also printed on the slide”) **and** 0s (“$99 a month”). Without rule 3, Gemma stared at 3.12s and said “the spoken number is not specified.” With it, it used the $99 line.

**What we did not do.** We do not OCR the JPEG. We do not reject answers that lack the word “gold.” We do not require speech for “what color is the printed number?” (color only).

### H5 — clap count (removed)

We had a bounce that said “if you are not sure, the count is zero.” That helps **this** tape (zero claps) and can make Gemma too shy on a file that **does** have claps. That bounce, the listen-first-for-how-many gate, and the “this window is zero” listen note are **gone**.

What stays, because it is true of CLAP on any file: sound hits are **times to listen**, not `count=` of events. The laptop still does not count claps in the WAV.

There was no extra H1 (“confirm $99 is on red”) laptop rule to remove. That was a trap question, not a code path.

---

## What else we did

- **Unit tests** on black 12s and ~1s mp4s, not this exam tape. They check skip / recut / print-vs-speech without mentioning beep / clap / ship / $99 as answers.
- **Did not** add Notion logging, a new database, a new UI, React, a clap model, or OCR.

Files: `backend/app/agent/loop.py`, `parts.py`, `schema.py`, tests in `test_loop_rules.py`, `test_chat.py`, `test_audio.py`.

---

## What is still open (honest)

| Item | Why it is still open |
|---|---|
| Skip in the last 6 seconds | By design. Lets a short file finish. |
| Counting a sound that is not there | No classifier. We will not bounce toward zero. |
| H1 trap (“confirm $99 is on red”) | No laptop rule. Gemma can still say “yes” to a false premise. |
| Gold vs yellow | Gemma’s color word. We do not OCR. |

---

## Bottom line

What we **kept** is loop hygiene for any file: don’t crawl 2s steps until the 12-move cap; don’t export the whole CLAP window from the previous scene; don’t export forever; if they asked print vs speech, open both books.

What we **removed** is the exam-shaped clap-count bounce (“say zero”). Counting events that aren’t in the WAV is still not a solved product feature.
