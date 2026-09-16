# Leftover live issues: what broke, what we changed, what is still open

Readable write-up of the leftover exam-tape problems, the laptop rules we added, the tests, and the live Modal Gemma runs. Not an answer key. Gemma still picks look / listen / spoken words / printed slides / sounds. The laptop only says how those books work.

Tape (16s): **0–6s** Pricing + gold/yellow **$99** (also spoken) → **6–10s** RED ALERT + silence → **10–16s** Q3 / “Ship the slide index” (never spoken) + a tone ~**11s**.

## The four leftovers (and two extra holes)

### 1. Walk the whole tape (H8)

**Problem.** Gemma walked 2 seconds at a time (look + listen). Each pair costs two of 12 moves. By ~9s the loop forced an answer. Q3 and the beep were never opened.

**Fix.** If the last look window matches the last listen window, the next look or listen starts at that end, and more than 6s of tape remain, **block** that step and say “skip ahead.”

**Found live.** Skip-ahead fired. Gemma still named Pricing, RED ALERT, and Q3. It does not always mention the beep in the final sentence.

**Still open.** Look-only 2s crawls are not blocked. Skip is off in the last 6s of a file.

### 2. Clip when the beep happens (H7)

**Problem.** Sound search returns a **window** (often 9–12s). The beep is near the **middle**. Exporting the whole window starts on RED ALERT.

**Fix (first).** If the export equals a sound-hit window, nudge a recut around the middle (~2s). Bounce answers until they recut.

**Found live.** First run: Gemma itself exported 11.5–14.5 (nudge idle). Second run: it exported 9–12, then recut **9.5–11.5** (centered on 10.5). That still included ~0.5s of red, and it cut off the tail of the tone after 11.5s.

**Fix (this pass).** Recut **from the middle forward** for ~2s, not ±1s around the middle. The start of a search window is often the previous slide. A 9–12 hit becomes ~**10.5–12.5** (capped at file end).

### 3. Printed number color vs speech (M1)

**Problem.** Gemma **did** look at Pricing and named **yellow $99**. It never opened spoken words, then said it could not tell if that matched “what they said.” Speech on this tape *does* say $99.

**Fix (first).** After a slide look: if you see a price or digits, that **is** the printed number — name the color.

**Fix (this pass).** If the question talks about something **printed** *and* **what they said**, refuse the answer until Gemma **searches spoken words**. Then it can say whether those lines match the pixels. We do not OCR the JPEG and we do not hardcode “gold” or “$99”.

**Still open.** Color word (yellow vs gold) is still Gemma’s. If it searches speech and still hedges, the bounce already fired.

### 4. How many claps? (H5)

**Problem.** Sound search is not a clap detector. It returns **times that are somewhat like** the query (false neighbors). Gemma treated those rows as a count, or heard silence/tone and still said “one clap.” The tape has **zero** claps.

**Fix (first).** Notes: hits are times to listen, not a count; unsure → zero.

**Found live.** Notes did not stick. After listening to 7.5–9s (silence), it still answered **one**.

**Fix (this pass).** Three laptop rules, still no clap list:

1. After a “how many …” question that already used `search_audio`, **do not answer until it listens**.
2. After it listens, bounce the first answer: hit rows are not the count; speech / silence / a different tone is **zero**; if unsure, the answer is **zero**.
3. Stronger listen note: this window is zero unless you clearly heard that exact sound.

**Still open.** There is no clap classifier. A second answer after the bounce can still invent a count. Live Gemma has to actually say zero.

## What else we did

- Unit tests on black 12s / 1s files (not the exam tape): speech-match bounce, how-many listen bounce, recut starts at the middle. The laptop notes still do not contain beep / clap / ship / $99.
- Same 16s tape on Modal Gemma 4 E4B, FastAPI on this machine, fresh chat per question. We do **not** call pass without HTTP 200.
- No new architecture, no React, no Notion tracker.

## Live scoreboard

Filled after each Modal rerun in [four leftover live issues](live-leftover-issues.md). This pass’s rerun is recorded there as **third live rerun**.
