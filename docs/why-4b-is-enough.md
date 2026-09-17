# Why 4B is enough

Plain note of leftover problems, what 4B vs 12B actually did on the live tape, and why the default brain stays **Gemma 4 E4B**.

The numbered labels (H7, H5, …) are only test ids. This file talks in questions.

**Closed.** The 12B A/B is done. Default stays **E4B**. The 12B Modal worker remains an optional side app. Next experiment is [E4B thinking on/off](e4b-thinking.md), not another 12B pass.

Related: [leftover issues](live-leftover-issues.md) · [leftover report](live-leftover-report.md) · [sound search is a range](sound-window-export.md) · [A/B plan + scoreboard](e4b-vs-12b-plan.md)

---

## How this machine works

Gemma never sees the whole video. Each turn it picks a **move**: look at photos, listen to a wav, search spoken words / pictures / sounds / printed slides, export a clip, or answer. The **laptop** runs that move and sends back what it found. Twelve moves, then we force an answer.

Sound search is **not** “the beep is at 11.00s.” It returns a **window of similar audio**, often **9–12s** on this tape. Exporting that window exports whatever is in it — including the previous slide.

The 16s exam tape (on purpose, speech / print / sound disagree):

| Time | On screen | Sound |
|---|---|---|
| 0–6s | Navy **Pricing**, gold/yellow **$99** | Someone **says** “$99” |
| 6–10s | **RED ALERT** | Silence |
| 10–16s | **Q3 / Ship the slide index** | A **tone** ~11.0–11.75s |

There are **zero claps**. Nobody says “Q3” out loud.

---

## What problems still exist

These are real product holes. They are **not** “4B is too small, so use 12B.”

### 1. Clip when the beep happens

**Ask:** make a short clip of whatever is on screen when the beep happens.

**Should:** listen at a sound hit, then export **the range you heard** (around the tone, Q3 on screen). Not the whole 9–12 search window (that still has RED ALERT at the start).

**What 4B did:** search sound → **export 9–12 with no listen**, then a second export 10–12.5. It never opened the wav. The laptop cut exactly those times. Flag: dumped an unheard search window.

**What 12B did:** search sound 9–12 → **listen 10.5–13.5** → export **10.5–13.5**. That is the original correct path. The cut is Q3 + beep, not red+Q3.

This is the **only** leftover 12B clearly won.

### 2. How many claps?

**Ask:** count the claps.

**Should:** **zero.** This tape has speech, silence, and a tone.

**What 4B did:** listened 7–9s. “I couldn’t clearly hear any claps.” Honest, not the word zero.

**What 12B did:** listened several windows and invented **five** claps.

Sound search returns **times that are a bit like the query**, not a count. The laptop never counts claps in the wav. A bigger brain did not fix this. It made it worse.

### 3. Tone + what is on screen

**Ask:** when the notification tone plays, what is on screen?

**Should:** Q3 / Ship the slide index (the tone is ~11s; red ended at 10s).

**What 4B did:** sound hit 9–12, then look+listen **10–13**. Named Q3 at 12s. **4B won this one.**

**What 12B did:** listened to the **whole 9–12 search window** and described **RED ALERT** (that is the **start** of the window, before the tone). Listening happened. The description was of the wrong part of the window.

### 4. Trap wording: is $99 on red?

**Ask:** a yes/no that is **false**. The price is on navy Pricing, not on RED ALERT.

**What 4B did:** looked at red, Pricing, and Q3. Answer started with **“Yes”**, then said yellow $99 on a **dark blue** background, matching the transcript. The pixels were right. The first word still sounds like it agreed with the trap. No extra laptop rule for this — it is how 4B wrote the sentence.

**What 12B did:** “The $99 price is **not** on a red emergency screen… dark blue Pricing… red is RED ALERT and has no price.” Clearer.

### Already fixed (keep)

**Walk the whole tape.** 4B used to crawl 2 seconds at a time and run out of moves before Q3. The laptop now **skips ahead** when a lot of file is still left. Both brains passed. That rule stays. It is not a 4B-vs-12B issue.

**Price / ship this quarter / printed number vs speech.** Both brains can open the books and answer. We **removed** the old “block answer until you search speech” bounce. Both opened speech on this run anyway.

---

## What 4B is good at

On the same eight questions, same tape, crutches **off**:

- Everyday asks: Pro cost, what to ship this quarter, walk the slides, printed $99 vs speech.
- Tone + screen, **this run**: jumped later inside the sound window and named Q3.
- Claps: did not invent a number (said it couldn’t hear any).
- Walking a long file: with skip-ahead, it names Pricing, RED ALERT, Q3.

4B is **not** good at: **search sound → listen → cut what I heard.** It searches, then exports the search window. That is the beep-clip fail. Older “passes” on that question used a recut-from-middle **crutch**. That crutch is gone. Without it, 4B still dumps 9–12.

---

## What 12B proved

12B is better at the **plan** “search sound → listen → export the heard range.” That is the beep clip. 4B does **not** already do that well.

12B did **not** prove:

- it is better at counting events in audio (it invented five claps),
- it is better at “what is on screen at the tone” (it named RED ALERT),
- we should switch the default brain.

Automated tally this run: 4B **6 pass / 1 partial / 1 fail**. 12B **5 pass / 2 partial / 1 fail**. Keep E4B as default. 12B stays a **second** Modal worker if we want listen-then-cut more often. We do not pay the extra worker for day-to-day chat.

---

## Four “wait, what?” bits

### Doesn’t 4B already search sound → listen → cut?

No. That sentence is about the **beep clip**, not about 4B in general.

4B **can** search, look, listen, and export. On “clip the beep” it **skipped listen**. It took the 9–12 search hit and exported 9–12. 12B listened first, then exported 10.5–13.5 (what it heard), not the mixed red+Q3 window.

If 4B already did that path well, we would not have needed the recut crutch, and this A/B would have been a tie on that question. It was not.

### 4B named Q3; 12B named RED ALERT — 12B did not win this one

Same sound hit: **9–12s**. Inside that window:

- **9–10s** is still RED ALERT (silence),
- **10s+** is Q3,
- the **tone** is ~11s.

4B’s next look was **later** (10–13) so the photos were Q3. 12B listened to **9–12** and described the first thing in that wav/photos: RED ALERT.

So: 12B **did** listen (good for clipping). It still described the **window start**, not the beep. 4B looked a bit later and named Q3. That is why the note said 12B did not win “tone + screen.” Do not put “always cut from the middle” back — that guesses this tape.

### 4B started with “Yes”, then mentioned dark blue. What?

The question is a **trap**: “is the $99 on the red screen?”

True facts: $99 is yellow on **navy/dark blue Pricing**. Speech also says $99. RED ALERT has no price.

4B answered a nearby true question (“does the printed price match speech?”) and led with **Yes**. Then it said dark blue. A reader can think the answer to “on red?” was yes. 12B answered the actual trap: **not on red**.

“No extra laptop rule” means: we are not going to bounce the word Yes, or hardcode “if they say red, say no.” That would be another exam crutch. The photos were already enough; 4B’s **wording** was messy.

### Should we add arithmetic / memory so it can count claps?

**No arithmetic on search hits.** That *is* the bug we already saw: treating “five similar-audio windows” as “five claps.” A calculator that adds hit rows would lock that bug in.

**Memory of looks does not hear claps.** Remembering “I saw RED ALERT at 6s” does not tell you how many hands clapped. Memory of “I already listened 7–9” only stops repeat listens; it still does not count events in the wav.

**What would actually count:** a **detector** on the audio (onset / clap classifier) that returns a number the laptop trusts. Until that exists, the honest answers are “I couldn’t clearly hear any” (4B this run) or **zero** when the wav is speech/silence/tone. Prompting “if unsure, say zero” is exam-shaped for *this* tape (a file with real claps could get pushed to zero). 12B inventing five is the failure mode to avoid.

So: do not add clap math. Do not restore “say zero.” Next step for counting, if we care, is a detector — not a bigger Gemma and not a memory of search rows.

---

## What we will not do

- Do **not** switch the default brain to 12B.
- Do **not** restore recut-from-middle, print-vs-speech bounce, or “say zero.”
- Do **not** bake this tape’s times into the loop (“if they say beep, jump to 11s”).
- Do **not** count CLAP hit rows as claps.

4B is enough for the product loop we shipped. 12B is a measured extra: better at listen-then-cut, worse at inventing clap counts, not a reason to change the default.

---

## Closed (12B A/B)

This comparison is finished. Do not merge that as a default-brain switch.

| Keep | Drop |
|---|---|
| Default **E4B** (`google/gemma-4-E4B-it`) | Switching FastAPI to 12B |
| 12B worker as an **optional** second Modal app | Another 12B hidden-intent pass |
| Skip-ahead (loop hygiene) | Recut / print-vs-speech / “say zero” crutches |

12B only clearly won **listen-then-cut** (clip the beep). It lost clap count (invented five) and, this run, tone+screen (named RED ALERT). Automated tally: E4B 6/1/1 vs 12B 5/2/1.

Next: turn **Gemma thinking** on for E4B and see if the planner starts listening before it exports. That is a separate note: [e4b-thinking.md](e4b-thinking.md).
