# Spoken words, then stop

Same 16s tape as the [hidden-intent suite](live-intent-questions.md). This note is only about one bug: Gemma searched **what was said**, then quit.

Video: `af12a3ad-c22d-4359-8de9-ec7baff9eb6a` (`live-test-talk.mp4`)

We did **not** hardcode words like beep, clap, or ship. Gemma still chooses look / listen / pictures / printed slides / sounds. The laptop only stops it from searching spoken words twice.

## The issue

When a question *sounds like talking* — “what are we supposed to ship this quarter?”, “what did they tell us to ship?”, “clip when the beep happens” — Gemma opens the spoken-word book first.

Those hits are often the **wrong lines**, not empty. Whisper returns “The pro plan is $99 a month” or “The number is also printed on the slide.” Gemma treats that as “I searched,” then apologizes or exports the pricing slide.

Nobody ever *says* “Ship the slide index.” That sentence is only printed on the Q3 slide (10s). The beep is a tone at ~11s, not a spoken word.

A second, smaller bug: the sound-search note used to say `merged events: count=`. Gemma read that number as **how many claps**, and answered “4 claps.” There are zero claps. Those windows are just times to listen.

## What we changed

Two notes in the loop. No new tools. No keyword list.

1. After a spoken-word search, the laptop says: those lines are **only what was said out loud**. If they do not answer, do a **different** move. Do not search spoken words again. The loop also **blocks** a second spoken-word search in the same question.
2. Sound hits are **times to listen**, not a count of events. The `count=` line is gone.

## Did it work?

Reran the questions that failed for this reason, plus three that already passed (so we did not break $99 / RED ALERT / the fake red-screen price). Fresh API chat each time. HTTP 200 unless noted.

| Q | Before | After | Verdict |
|---|---|---|---|
| **M3** “What are we supposed to ship this quarter?” | Speech only. Missed the printed line. | Speech → printed slides → look 10–12s. “Ship the slide index this quarter (Q3 Roadmap).” | **Pass.** This is the fix. |
| **H2** “Right after the warning screen, what did they tell us to ship?” | Speech three times. Quoted $99. | Same path as M3. Got “Ship the slide index.” Mixed up “warning” vs Q3 a bit, but the printed answer is right. | **Pass.** |
| **H7** “Clip when the beep happens.” | Searched speech for “beep.” Exported **pricing** 3.1–6.1s. | Speech → **sounds** → look 9–12s → export **9–12s**. | **Partial.** It switched books (that is new). The clip covers the beep at 11s, but 9s is still RED ALERT, so it is not a clean Q3 cut. |
| **H5** “How many claps?” | Invented **4 claps** from `count=`. | Did not invent 4. Also did not listen. Just said it cannot count. | **Fail.** Hallucination gone; still no “zero.” |
| **H8** Walk the whole tape | Refused. | Still refused. | **Fail.** This fix does not make it tour a 16s tape. |
| **M1** Color of the printed number | Looked at Q3, skipped Pricing. | First try **422** (bad JSON). Retry: looked at Q3 and red, still skipped Pricing at 0s. | **Fail.** Wrong slide ranking, not this bug. |
| **M4** Tone + what’s on screen | Sound 9–12s, looked at 9s, said RED ALERT. | Same. | **Partial.** Unchanged. A 3s sound window still starts on red. |
| **E1** “How much does Pro cost?” | $99 from speech. | Still $99 from speech. | **Pass.** |
| **E2** Big white letters on red | RED ALERT from slides. | Still RED ALERT. | **Pass.** |
| **H1** “$99 is on the red screen?” | No; red is RED ALERT. | No; looked at red and at Pricing. | **Pass.** |

**Bottom line:** the thing we aimed at worked. “Ship this quarter” and “what did they tell us to ship” now leave spoken words and **read the slide**. “Beep” now opens the sound book instead of exporting the price slide. Easy questions that should stay on speech or pictures still do.

Gemma is not a switch. One later M3 retry answered “I cannot…” with **no search at all** (the note never fired). Three retries after that all did speech → printed slides → look 10s → “ship the slide index.” The watch page did the same after one 422 (Gemma returned no JSON): **“For the Q3 Roadmap, we are supposed to ship the slide index.”** Details: search → search_slides 10–16s → look 10–12s. So: when it *does* open spoken words first, it now switches. It can still refuse or 422 before any move.

What this did **not** fix: walking the whole tape, counting claps as zero, looking at the *start* of a 3s sound hit (red at 9s vs beep at 11s), or ColQwen ranking “printed number” onto Q3 instead of Pricing.
