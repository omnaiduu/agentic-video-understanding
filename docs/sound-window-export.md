# Sound search returns a range, not a pin

This is leftover issue **H7** (clip when the beep happens). It is a real product issue, not an exam trick. The laptop should **not** guess the middle and recut. The original (correct) path is: **search_audio → listen → export the range you heard.**

Related: [why 4B is enough](why-4b-is-enough.md) · [four leftover live issues](live-leftover-issues.md) · [E4B vs 12B plan](e4b-vs-12b-plan.md)

---

## How sound search actually works

`search_audio` is **CLAP**. It does not say “the event is at 11.00s.” It embeds the query phrase and finds **chunks of audio that are similar**.

Those chunks are **windows**:

- Default chunk length is **3 seconds**, hop **1.5 seconds**.
- A hit looks like `[9.0s–12.0s] score=0.91`, plus a `middle=` number that is only the midpoint of that window.
- The **event** (a short tone, a clap, a door) often sits **somewhere inside** that window. On this tape it is near the middle. That is a coincidence of hop/chunk size, not a contract.
- The **start** of the window is often the **previous scene**. On the 16s exam tape, 9s is still **RED ALERT**. The tone is ~11.0–11.75s. Q3 starts at 10s.

The laptop **cuts exactly the times Gemma asks for**. If Gemma says `export_clip` 9–12, the file is 9–12. The laptop cannot hear the wav and pick the beep. There is no onset detector on the export path.

So: **exporting a CLAP range is exporting a range.** Sometimes that range is what the user wanted. Often it includes the previous slide and extra silence.

---

## What we used to do (fragile)

E4B on Modal usually did:

1. `search_audio` → hit **9–12**
2. `export_clip` **9–12** (no listen)
3. Answer with that URL

The clip mixed red + Q3 + the tone.

We then **hardcoded a recut**:

- Remember each sound-hit `[start, end]`.
- If the export matched that window (±1s), append “that is the whole search window; export again from the **middle** for ~2s, not before the middle.”
- Bounce `answer` until that recut existed.
- After a short clip, **block** more exports (E4B had started walking 11.5–14.5 → 13.5–15.5 → 15.5–16).

That **did** make one live pass: 9–12 then **10.5–12.5**. It is still the wrong architecture:

- It assumes the event is at the **midpoint**. Hop/chunk size made that true *here*. A 0.5s tone at the start of a 3s window would be cut off.
- It **guesses** instead of listening. Gemma can hear. The laptop cannot.
- It is **prompt + bounce**. E4B ignored notes when they were inconvenient. A second export death-spiral needed yet another gate.
- It fights the truth of the book: the book returned a range; we punished exporting that range.

`middle=` on the hit line can stay as **information**. Forcing “cut starting at the middle” cannot.

---

## What we do now (OG path)

1. Sound hits are **times to listen**, not a count, not a pin.
2. The observe note says: a hit is a **similar-audio range**; the start can be a different moment; **listen at a hit**; if the user wants a clip, **export the range you heard**.
3. The laptop **does not** recut, bounce, or block a second export.
4. If Gemma exports the whole CLAP window without listening, **that cut is what we ship**. That is an honest fail for a small model. On this tape, **12B listened then exported the heard range**; **E4B still dumped 9–12**. See [the A/B](e4b-vs-12b-plan.md).

Unit tests (black 12s file, not this tape):

- `search_audio` → `listen` 9–12 → `export_clip` 10.8–12 → answer is accepted. No “whole search window” note.
- `search_audio` → `export_clip` 9–12 → answer is accepted. The range is the range.
- A second export after a listen is allowed (so it can tighten after hearing).

---

## Why this is not “just a code error”

It *looks* like a bug because 9–12 is the wrong clip. The code is doing what it was told: **cut these seconds**. The mistake is treating CLAP like an event detector.

A detector (onset, clap classifier) would be a new index. Out of scope. Until that exists, the only honest pin is **Gemma’s ear** on a wav we attach.

Skip-ahead (H8) is different: that is loop hygiene about the 12-move budget. Recut-from-middle was us pretending to hear.
