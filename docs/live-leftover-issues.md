# Four leftover live issues

Same 16s tape as the [hidden-intent suite](live-intent-questions.md). It names the four questions that still fail after [spoken words, then stop](live-spoken-words.md), the laptop rules we added, and what has been proven.

Video: `af12a3ad-c22d-4359-8de9-ec7baff9eb6a` (`live-test-talk.mp4`)

We will **not** hardcode this file (no “if they say beep, jump to 11s”). Gemma still picks look / listen / spoken words / printed slides / sounds. The laptop only adds rules about **how those books work**.

## Context you need

Gemma does not get the whole video. Each turn it picks a **move** (look at photos, listen to sound, search a book, export a clip, or answer). The **laptop** runs that move and sends back what it found. That back-and-forth is the **loop**.

We allow **12 moves**, then we force an answer. One look may attach at most **12 photos**. Those caps exist because Gemma’s prompt is small; dumping the whole file blows it up.

The exam tape, in order:

- **0–6s** — printed **Pricing**, gold **$99**. Someone **says** “$99.”
- **6–10s** — printed **RED ALERT**. Silence.
- **10–16s** — printed **Q3 / Ship the slide index** (never spoken). A **tone** around **11s**.

Speech, print, and sound disagree on purpose.

Already shipped (not these four): spoken-word search is only speech; sound hits are times to listen, not a clap count; no answer on turn 1 with zero looking/listening; a look is capped at 12 photos.

---

## 1. Walk the whole tape (H8)

**What we asked:** go through the video in order and tell us everything.

**What should happen:** Pricing / $99, then RED ALERT, then Q3 and the beep.

**What happens:** Gemma starts at 0s and takes **two-second** looks and listens: 0–2, then 2–4, then 4–6… Each look *or* listen costs one of 12 moves. Two moves cover two seconds of tape. By ~9s the loop says “answer now.” Q3 (10s+) and the beep (~11s) were never opened.

This is **not** us cancelling the walk. Gemma *is* walking, in tiny steps. The **move budget** runs out first. The books already know 10s and 11s; this question never jumps there.

**Simple fix:** stop the 2-second crawl when a lot of the file is still left. Say “you already did that beat — look several seconds later, the video goes until 16s.”

**A bit more technical:** if the last look window matches the last listen window, the next look *or* listen starts at that end (~2s step), and more than **6s** of video remain, **block** that move and tell it to skip ahead. Tiny 1s test files would not fire (not enough tape left). Do **not** “fix” this by raising 12 rounds — that only attaches more photos.

**In code now.** Unit tests (black 12s file, not the exam tape): paired look+listen then 2–4 is blocked; look-only 2–4 is blocked; a jump to 8–10 is allowed; 1s files do not skip. **Live pass** on Gemma + this tape (skip 2–4, then RED ALERT and Q3).

---

## 2. Clip when the beep happens (H7)

**What we asked:** export a short video of the beep.

**What should happen:** a tight cut around ~11s (Q3 + the tone), about **2 seconds**, not the red slide.

**What happens:** sound search does not return “beep at 11.00s.” It returns a **window** of audio that is *similar* to the query, often **9–12s**. The beep sits near the **middle**. The **start** of that window is still RED ALERT. Gemma then exports **9–12** because that is the hit it was given. The laptop cuts exactly those times. Result: red **and** Q3, beep somewhere inside.

**Simple fix:** if they export the **whole** search window, make them cut again around the **middle** (~2s), not the full 3s.

**A bit more technical:** remember sound-hit `[start, end]`. If `export_clip` matches that window (± a fraction of a second), append “recut from the middle for about 2 seconds, not before the middle.” If they **answer** while that full-window export is still the clip, bounce until they recut. When they export a shorter window that no longer matches the hit bounds, let the answer through.

**In code now.** Unit tests: sound hit 9–12 → export 9–12 is nudged; two answers on that clip are both bounced; export 10.5–12 is accepted; an unrelated 0–2 cut is not nudged. Recut window is **from the middle forward** (~2s). A second export after a short clip is blocked. **Live pass:** 9–12 then **10.5–12.5**.

---

## 3. Color of the printed number (M1)

**What we asked:** the number **on the slide**, its **color**, and whether it matches speech.

**What should happen:** gold **$99** on Pricing; speech also says $99, so they match.

**What happens:** printed-slide search returns several times. Gemma **does** look at Pricing (0s). The photo **does** show gold $99. It still **hedges** (“might be gold,” “not sure if it matches”). Search worked. The final sentence is vague. Several slides are in the prompt at once, and speech also says $99, so it will not commit.

**Simple fix:** after a look, say: if you can see a price or digits, that **is** the printed number — **name the color**. If they spoke a number, say whether it matches. Do not stop at “there appears to be a price.”

**A bit more technical:** this is a stronger **observation note** after `look`, plus the existing “next unused slide time” rule so Pricing is not skipped. We **cannot** guarantee the words “gold” without hardcoding this tape. The laptop does not OCR the JPEG or reject answers that lack a color word (that would be a new checker). Hedging may still happen; the note makes the expected shape of the answer explicit.

**In code now.** After a slide look: name the color. If the question is print **and** “what they said,” **block the answer** until spoken-word search has run, then compare those lines to the printed digits. **Live pass** (yellow 99 matches spoken $99).

---

## 4. How many claps? (H5)

**What we asked:** count the claps.

**What should happen:** **zero.** This tape has speech, silence, and a tone. No claps.

**What happens:** sound search is **not** a clap detector. It finds chunks *somewhat like* the query. It can still return **times** (false neighbors). After a listen, Gemma sometimes says **zero**, sometimes treats the **tone** or the **number of windows** as claps. The laptop never counts claps in the WAV. So the answer **flips between runs**.

**Simple fix:** after sound search and after listen: only the **sound in the question** counts. Speech, silence, or a **different** tone is not a match. If you are not sure, the count is **zero**. Do not use the number of search windows as the count.

**A bit more technical:** still prompt-only. There is no clap classifier on the laptop. A real fix would be a detector (out of scope). Bouncing a count with **no** listen is cheap; bouncing a wrong count **after** a listen is guessing what the WAV contained. Expect this to stay **unstable** until a listen-then-zero note sticks more often.

**In code now.** **Removed.** The listen-first / “unsure → 0” bounce was exam-shaped (this tape has zero claps; a real file with claps could be pushed toward zero). Sound search still describes hits as **times to listen, not a count** (that is true of CLAP on any file). There is no clap detector.

---

## Concise

| Issue | In one line | Laptop rule | Proven? |
|---|---|---|---|
| **H8 walk** | 2s look+listen burns 12 moves by ~9s | Skip the next 2s step when >6s remain (look-only too) | **Live pass.** Skip 2–4; named Pricing, RED ALERT, Q3 |
| **H7 beep clip** | Exports the whole 9–12s sound window | Recut from the middle **forward** ~2s; block extra exports after a short clip | **Live pass.** 9–12 then **10.5–12.5** (Q3 + beep, not red) |
| **M1 gold $99** | Saw the pixels; would not name color + match | Name the color; **block answer** until spoken-word search; then compare lines | **Live pass.** Yellow 99 matches spoken $99 |
| **H5 claps** | Sometimes 0, sometimes invents claps from silence/tone | *(removed)* No “say zero” bounce. Hits remain times, not a count | **Not a laptop fix.** Trap question on this tape |

**Not a fix:** a list of words for this video (beep → 11s, claps → 0, printed number → gold). That would pass the exam and fail the next file.

## Live rerun (Modal Gemma, this machine)

Same 16s tape recipe (Pricing / RED ALERT / Q3 + ~11s tone). New upload id `c1d9beb7-5465-4f47-9d53-2d6b299104b5`. Gemma 4 E4B on Modal. Fresh chat session per question. HTTP 200 unless noted.

| Q | After this PR | Verdict |
|---|---|---|
| **E1** Pro cost | Speech (+ extra looks). “$99 a month.” | **Pass.** |
| **H1** $99 on red? | Looks 6s, 10s, **and 0s**. Price is not on red. | **Pass.** |
| **M3** ship this quarter | Speech → slides → look 10s. “Ship the slide index.” | **Pass.** |
| **M4** tone + on screen | Sound hit 9–12 → **look 10.5–12**. Q3 / Ship the slide index. | **Pass.** Middle-of-window, not red at 9s. |
| **H8** walk the tape | look+listen 0–2, **skip 2–4**, then 6–8, 10–12, 14–16. Names Pricing $99, RED ALERT, Q3 / ship the slide index. | **Pass.** Skip-ahead fired on live Gemma. Did not mention the beep in the sentence. |
| **H7** clip on the beep | Sound 9–12 → export **11.5–14.5** (Q3 only, not 9–12 red+Q3). | **Pass** on the leftover (not the whole search window). Starts a bit after the 11.0s onset. |
| **M1** printed number color | Looks 10, **0**, and 6. Says **yellow $99**. Then: cannot confirm it matches speech (it never searched speech). | **Partial.** Color + next unused slide worked. Speech match still hedged. |
| **H5** how many claps | Sound search, listen 13.5–14.8 and 7.5–9 (silence). Still talks as if it heard claps; no **zero**. | **Fail.** Notes did not stick. |

**Where tests still show a hole**

- Look-only crawls are skipped the same way as look+listen crawls (remaining > 6s). Skip is still off in the last 6 seconds of a file.
- Skip-ahead does not fire in the last 6 seconds of a file.
- H5 exam bounce (“unsure → 0”) was removed. Sound hits are still times, not a count.

## Final live rerun (after speech-match, count bounce, recut-from-middle, look-only skip, extra-export cap)

Same tape `c1d9beb7-5465-4f47-9d53-2d6b299104b5`. Gemma 4 E4B on Modal. All eight HTTP **200**.

| Q | This run | Verdict |
|---|---|---|
| **E1** Pro cost | Speech. “$99 a month.” | **Pass.** |
| **H1** $99 on red? | Looks 0, 6, and 10. Finds $99 at 0s. Leads with “Yes” (the trap). Does not clearly say “not on red.” | **Partial.** |
| **M3** ship this quarter | Speech → slides → look 10s. “Ship the slide index.” | **Pass.** |
| **M4** tone + on screen | Sound 9–12 → look+listen **10.5–12.5**. Q3 / Ship the slide index. | **Pass.** |
| **H8** walk the tape | look+listen 0–2, **skip 2–4**, then 8–10 (RED ALERT), 12–14 and 14–16 (Q3). Names Pricing $99, Red Alert, Q3. | **Pass.** |
| **H7** clip on the beep | Sound 9–12 → export **9–12** → recut **10.5–12.5**. | **Pass.** Nudge fired. Cut is Q3 + beep, not red. |
| **M1** printed number color | Looks 10, **0**, and 6, then **search speech**. Yellow 99 matches spoken $99. | **Pass.** |
| **H5** how many claps | Sound search, listen 7.5–9.5. “Cannot definitively count.” | **Partial.** No invented “one clap.” Still not **zero**. |

## Second live rerun (same tape, same Modal Gemma)

Independent chat sessions after the first scoreboard. Same upload `c1d9beb7-5465-4f47-9d53-2d6b299104b5`. All eight questions HTTP **200**.

| Q | This run | Verdict |
|---|---|---|
| **E1** Pro cost | Speech + looks. “$99 a month” on the 0s slide. | **Pass.** |
| **H1** $99 on red? | Looks red, Pricing, Q3. Price is yellow on dark blue, not on red. | **Pass.** |
| **M3** ship this quarter | Speech → slides → look 10s. “Ship the slide index.” | **Pass.** |
| **M4** tone + on screen | Sound 9–12 → look+listen **10.5–12**. Q3 / Ship the slide index. | **Pass.** |
| **H8** walk the tape | look+listen 0–2, **skip 2–4**, then 8–10 (RED ALERT) and 14–16 (Q3). Names Pricing $99, RED ALERT, Q3. | **Pass.** Skip-ahead fired. No beep in the sentence. |
| **H7** clip on the beep | Sound 9–12 → export **9–12** → recut **9.5–11.5**. | **Pass** on the leftover (nudge fired). Clip still includes ~0.5s of red before Q3; beep onset is in the cut, tail after 11.5s is not. |
| **M1** printed number color | Looks 10, **0**, and 6. **Yellow $99.** Then: no spoken number heard, cannot confirm match. | **Partial.** Same hole as run 1. |
| **H5** how many claps | Sound search, listen 7.5–9 (silence / red). Answers **one** clap. | **Fail.** |
