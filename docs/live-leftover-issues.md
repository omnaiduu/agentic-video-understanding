# Four leftover live issues

Same 16s tape as the [hidden-intent suite](live-intent-questions.md). This note is **not** a live rerun. It names the four questions that still fail after [spoken words, then stop](live-spoken-words.md), and whether we have a fix.

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

**A bit more technical:** if the last look window matches the last listen window, the next look starts at that end (~2s step), and more than ~4s of video remain, **block** that look and tell it to skip ahead. Tiny 1s test files would not fire (not enough tape left). Do **not** “fix” this by raising 12 rounds — that only attaches more photos.

**Is there a solution?** Yes. Laptop rule, not an answer key. Not live-proven yet.

---

## 2. Clip when the beep happens (H7)

**What we asked:** export a short video of the beep.

**What should happen:** a tight cut around ~11s (Q3 + the tone), about **2 seconds**, not the red slide.

**What happens:** sound search does not return “beep at 11.00s.” It returns a **window** of audio that is *similar* to the query, often **9–12s**. The beep sits near the **middle**. The **start** of that window is still RED ALERT. Gemma then exports **9–12** because that is the hit it was given. The laptop cuts exactly those times. Result: red **and** Q3, beep somewhere inside.

**Simple fix:** if they export the **whole** search window, make them cut again around the **middle** (~2s), not the full 3s.

**A bit more technical:** remember sound-hit `[start, end]`. If `export_clip` matches that window (± a fraction of a second), append “recut ~1s either side of the middle.” If they **answer** while that full-window export is still the clip, bounce once and ask for the recut. When they export a shorter window that no longer matches the hit bounds, let the answer through.

**Is there a solution?** Yes. The laptop rewrites the *cut*, not the word “beep.” Not live-proven yet.

---

## 3. Color of the printed number (M1)

**What we asked:** the number **on the slide**, its **color**, and whether it matches speech.

**What should happen:** gold **$99** on Pricing; speech also says $99, so they match.

**What happens:** printed-slide search returns several times. Gemma **does** look at Pricing (0s). The photo **does** show gold $99. It still **hedges** (“might be gold,” “not sure if it matches”). Search worked. The final sentence is vague. Several slides are in the prompt at once, and speech also says $99, so it will not commit.

**Simple fix:** after a look, say: if you can see a price or digits, that **is** the printed number — **name the color**. If they spoke a number, say whether it matches. Do not stop at “there appears to be a price.”

**A bit more technical:** this is a stronger **observation note** after `look`, plus the existing “next unused slide time” rule so Pricing is not skipped. We **cannot** guarantee the words “gold” without hardcoding this tape. The laptop does not OCR the JPEG or reject answers that lack a color word (that would be a new checker). Hedging may still happen; the note makes the expected shape of the answer explicit.

**Is there a solution?** Partial. We can push it to read pixels and compare to speech. We cannot honestly promise “gold” every run without cheating.

---

## 4. How many claps? (H5)

**What we asked:** count the claps.

**What should happen:** **zero.** This tape has speech, silence, and a tone. No claps.

**What happens:** sound search is **not** a clap detector. It finds chunks *somewhat like* the query. It can still return **times** (false neighbors). After a listen, Gemma sometimes says **zero**, sometimes treats the **tone** or the **number of windows** as claps. The laptop never counts claps in the WAV. So the answer **flips between runs**.

**Simple fix:** after sound search and after listen: only the **sound in the question** counts. Speech, silence, or a **different** tone is not a match. If you are not sure, the count is **zero**. Do not use the number of search windows as the count.

**A bit more technical:** still prompt-only. There is no clap classifier on the laptop. A real fix would be a detector (out of scope). Bouncing a count with **no** listen is cheap; bouncing a wrong count **after** a listen is guessing what the WAV contained. Expect this to stay **unstable** until a listen-then-zero note sticks more often.

**Is there a solution?** Partial. We can stop presenting hits as a counter (already done) and tighten the listen note. We cannot guarantee “zero” without hardcoding claps.

---

## Concise

| Issue | In one line | Fix? |
|---|---|---|
| **H8 walk** | 2s look+listen burns 12 moves by ~9s | **Yes** — block the next 2s step when >4s of tape remains; skip ahead |
| **H7 beep clip** | Exports the whole 9–12s sound window | **Yes** — if the cut equals a hit window, recut ~2s around the middle |
| **M1 gold $99** | Saw the pixels; would not name color + match | **Partial** — after look: name the color; say if speech matches. No OCR |
| **H5 claps** | Sometimes 0, sometimes invents claps from silence/tone | **Partial** — query sound only; unsure → 0. No clap detector |

**Not a fix:** a list of words for this video (beep → 11s, claps → 0, printed number → gold). That would pass the exam and fail the next file.
