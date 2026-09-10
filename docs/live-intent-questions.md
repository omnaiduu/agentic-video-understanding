# Hidden-intent live test

Same 16s tape as [live-query-retest](live-query-retest.md). This time **nobody named the tool**. No “look”, “listen”, “search slides”, or timestamps. Easy / medium / hard. Some questions plant a false idea on purpose.

**12 passed, 1 partial, 6 failed** (19 questions). Browser re-ran 3 of them.

After the [spoken-words-then-stop](live-spoken-words.md) notes, we **reran the failures**. **M3 and H2 now pass** (they leave speech and read the printed “Ship the slide index”). **H7 is partial** (opens the sound book, still exports 9–12s which mixes red + Q3). H5 / H8 / M1 still fail; M4 is still partial. Easy checks E1, E2, H1 still pass.

Video: `af12a3ad-c22d-4359-8de9-ec7baff9eb6a` (`live-test-talk.mp4`)

## What is actually on the tape

| Time | On screen | Sound |
|---|---|---|
| 0–6s | Navy slide: **Pricing** / gold **Pro $99** / per month | Speech: “The pro plan is $99 a month.” then “The number is also printed on the slide.” |
| 6–10s | Solid red: **RED ALERT** | Silence |
| 10–16s | Dark green: **Q3 Roadmap** / **Ship the slide index** | A tone ~**11.0–11.75s**, then silence |

Nobody ever *says* “ship the slide index” or “Q3”. That text exists only as pixels.

The last retest said the beep was at the end (13.5–16s). **That was wrong.** The wav is quiet after 11.75s. Several questions below exist to catch that.

## Why these questions

The earlier suite asked things like “Look at 0 to 2 seconds” and “Find the beep”. The model did not have to guess *which book* to open.

This suite asks the way a person would: “How much does Pro cost?”, “What are we supposed to ship this quarter?”, “I think $99 is on the red screen — confirm?” The laptop still only has look / listen / search speech / search pictures / search sound / search slides / export. The model has to pick.

## Scoreboard

| Level | Pass | Partial | Fail |
|---|---|---|---|
| Easy (E1–E4) | 4 | 0 | 0 |
| Medium (M1–M6) | 3 | 1 | 2 |
| Hard (H1–H8) | 5 | 0 | 4 |
| **Total** | **12** | **1** | **6** |

---

## Easy — natural questions, one fact

### E1. “How much does Pro cost?”

- **Expected:** $99 a month. Speech, slides, or a look at 0s all work.
- **Did:** Searched the transcript. “The pro plan is $99 a month.”
- **Verdict: pass.** It did not need to be told “search speech”.

### E2. “What's written in the big white letters on the bright red background?”

- **Expected:** RED ALERT. Must find the red frame, then look. Must not paste $99 onto it.
- **Did:** Picture search → look 6–7s → “RED ALERT”.
- **Verdict: pass.** Pixel description was enough; no tool name needed.

### E3. “Is anyone speaking in the last couple of seconds?”

- **Expected:** No. Last seconds are silent (the tone is at 11s).
- **Did:** Searched the transcript (hits only at 0s and 3.1s). Said no.
- **Verdict: pass, cheap method.** Right answer, but it never *listened* to the end. If Whisper had missed a last line, this would still look fine.

### E4. “Save a short downloadable video of just the first slide.”

- **Expected:** An export of the Pricing slide (0–6s).
- **Did:** Exported **0–2s**. That is still Pricing, just not the whole slide duration.
- **Verdict: pass.** It knew “save a video” meant export, without the word export.

---

## Medium — the wording points at the wrong book

### M1. “They said a number is also printed on the slide. What color is that number, and does it match what they said?”

Needs **speech and pixels**. The number is gold/yellow **$99** on the navy slide.

- **Did first:** HTTP **500**. Two `listen` clips in one prompt; Gemma allows only one wav. Fixed in code (drop the old wav).
- **Did after fix:** Slide search for “number printed on the slide” ranked **Q3, then Pricing, then red**. It looked at Q3 (no number), then **skipped Pricing** and looked at red. Answer: cannot confirm a printed number.
- **Verdict: fail.** The right slide was hit #2 (0s) and it never opened it. Vague query “number” is a weak ColQwen phrase; the loop also did not walk the ranked list in order.

### M2. “There's a moment the whole frame turns a warning color. What does it say, and is anyone talking then?”

Never says red, alert, look, or listen.

- **Expected:** RED ALERT, and silence.
- **Did:** Picture search → look 6–7s → listen 6–7s → “RED ALERT”. “There is no talking in that moment.”
- **Verdict: pass.** Best medium question. It picked two channels without being told.

### M3. “What are we supposed to ship this quarter?”

Sounds like a **speech** question. The answer is **only printed**: “Ship the slide index” on Q3. Whisper never heard it.

- **Did (API):** Searched the transcript three times. “The transcript does not contain information…”
- **Did (browser):** Same miss. Details: `search 3.1s` only. Never `search_slides`, never a look at 10s.
- **Verdict: fail.** This is the main limit: if the sentence sounds spoken, it will not open the slide book.
- **After the spoken-words note:** Speech → printed slides → look 10–12s. “Ship the slide index this quarter (Q3 Roadmap).” **Pass.** See [spoken words, then stop](live-spoken-words.md).

### M4. “When does the notification tone play, and what is on screen at that moment?”

- **Expected:** Tone ~11s. Screen is **Q3 Roadmap**, not red.
- **Did:** Sound search hit **9–12s** (the 3s chunk that contains the beep). Listened 9–12s. Then looked at **9s**, which is still **RED ALERT** (red lasts until 10s). Answer: tone 9–12s, screen is RED ALERT.
- **Verdict: partial.** Right sound book, wrong frame. It trusted the *start* of a 3s audio window instead of the actual beep at 11s.

### M5. “How many different slides are there, and what is the heading of each?”

- **Expected:** Three: Pricing, RED ALERT, Q3 Roadmap.
- **Did (API, fresh session):** Slide search returned 10s, 6s, 0s. Looked at all three. Named all three headings.
- **Did (browser, after other chats):** Found three hits, looked at 0s and 6s, **looked at 0s again** instead of 10s. Named Pricing and Red Alert; said it could not see the third heading.
- **Verdict: pass on API, weaker in a long UI session.** Surprise: it *can* enumerate slides when it spends the looks. Limit: a busy session wastes a look and misses Q3.

### M6. “Give me a downloadable clip of just the red warning so I can send it to someone.”

- **Expected:** Export overlapping 6–10s.
- **Did:** Picture search → look 6s → export **6–7s**.
- **Verdict: pass.** Short clip, correct slide, no “export” in the question.

---

## Hard — traps, absences, multi-hop

### H1. “I think the $99 price is on the red emergency screen — can you confirm?”

False premise on purpose.

- **Expected:** No. Red says RED ALERT. Price is on Pricing at 0s.
- **Did:** Looked at the red frames. Did **not** copy $99 onto them. Said the red screen has no price. Mentioned $99 only from the transcript at 0s.
- **Verdict: pass.** The thing we were afraid of (pasting the question’s $99 onto the wrong photo) did not happen.

### H2. “Right after the warning screen, what did they tell us to ship?”

“Tell us” pushes speech. After red they **do not talk**. The next slide prints “Ship the slide index”.

- **Did:** Transcript search three times (~67s). Apologized. Quoted only the $99 lines.
- **Verdict: fail.** Same limit as M3. It will not switch books when the first book is empty.
- **After the spoken-words note:** Speech → printed slides → look 10–12s. Answer includes “Ship the slide index.” **Pass.**

### H3. “The last slide raised the price to $199, didn't it?”

Second trap.

- **Did (API):** Slide search, looked at 0s, 6s, **and 10s**. “No… $99… Q3 Roadmap… red alert. Not $199.”
- **Did (browser):** Looked only at 0–2s Pricing. Still said $99, not $199. Did not describe the last slide.
- **Verdict: pass.** It refused the planted $199. API version actually inspected the last slide; UI version only checked the price slide.

### H4. “Is there a person, a bird, or a live camera in this tape?”

- **Expected:** No — slides only.
- **Did:** Picture search + looks at Pricing frames. No person, no bird.
- **Verdict: pass.** It did not invent a bird. It only inspected early frames, which was enough here.

### H5. “How many claps are in this recording?”

- **Expected:** Zero. Speech, silence, one beep. No claps.
- **Did first:** HTTP **422** (Gemma returned invalid JSON, no successful step to stitch).
- **Did retry:** Sound search. Treated overlapping 3s windows as “4 merged sound events” and **called them claps**.
- **Verdict: fail.** The sound book returns *similar windows*, not a clap count. The model trusted that list as a count.
- **After dropping `count=`:** Did not invent 4 claps. Also did not listen. Said it cannot count. Still **fail** (no “zero”).

### H6a / H6b. “What's the monthly price?” then “During the alarm, is that price still visible?”

- **Expected:** $99, then **no** — alarm/red has no price.
- **Did:** $99 from speech. Follow-up: looked at red. “No… screen shows RED ALERT.”
- **Verdict: pass.** Memory + a new look. “That price” / “the alarm” was enough.

### H7. “Make a three-second clip of whatever is on screen when the beep happens.”

- **Expected:** Find the beep (~11s), export ~3s of **Q3**.
- **Did:** Searched **speech** for “beep”. Hit the line at 3.12s (“The number is also printed on the slide”). Exported **3.1–6.1s Pricing**.
- **Verdict: fail.** “Beep” went to Whisper, not the sound book. The clip is the wrong beat.
- **After the spoken-words note:** Speech → sound search → look 9–12s → export **9–12s**. **Partial.** It left speech (that is the fix). The clip covers the beep at 11s but still includes red at 9s.

### H8. “Walk through the whole tape in order… including things nobody said out loud.”

- **Expected:** Pricing + speech, silent RED ALERT, Q3 + tone.
- **Did:** Immediate apology. No look, no search. “Beyond my current capabilities.”
- **Verdict: fail.** A 16s tape is small enough. The model refused instead of doing three short looks.

---

## Browser (same three questions a person would type)

Watch page, chat enabled, all four indexes ready.

1. **Ship this quarter** — same fail as M3: speech search only. Printed “Ship the slide index” is on screen at 10s and it never looked.
2. **$199 trap** — pass: “Pro is $99 per month, not $199.”
3. **How many slides / headings** — partial vs API: three hits, named Pricing and Red Alert, skipped looking at 10s so it never read **Q3 Roadmap**.

The UI showed Details (`search` / `search_slides` / `look`) under each bubble. No chat lock, no 500 in the browser pass.

---

## What surprised us (it *can* do this)

- **E2 / M2:** Describe a color and it finds the red frame, then looks, then (M2) listens. No tool names.
- **H1 / H3:** False prices in the question do **not** get copied onto the wrong slide if it actually looks.
- **M5 (fresh chat):** It counted **three unique slides** and read all three headings. That is more than “search one string”.
- **E4 / M6:** “Save” / “send someone a clip” is enough to export. No “export” in the sentence.
- **H6b:** “That price” + “the alarm” uses the last turn and then looks at red.

## Limits we know now

1. **Spoken wording used to mean “search speech and stop.”** After the loop notes, M3 / H2 leave speech and read the printed slide. Gemma can still refuse before any search, or 422 if it returns no JSON.
2. **“Beep” / “clap” in English ≠ the sound book.** H7 searched talk for “beep”. H5 treated CLAP windows as a clap *count* (there are zero claps).
3. **A 3s sound hit is not the event time.** M4’s beep is at 11s; looking at 9s (start of the window) still shows red.
4. **ColQwen ranking is only as good as the query.** “Number printed on the slide” ranked Q3 first. Hit #2 was the $99 slide and Gemma skipped it.
5. **One wav per prompt.** Two listens used to 500. The loop now drops the old clip. Color+speech questions can finish; they can still look at the wrong slides (M1).
6. **Cold Gemma is 503.** First wave of this suite 500’d until the GPU woke. Client now retries 503.
7. **“Summarize the whole tape” gets a refusal**, not three looks.
8. **Long UI sessions waste looks.** Same heading question that passed on a fresh API session missed Q3 in the browser thread.

## Fixes that landed because of this pass

- Retry Gemma HTTP 503 (cold GPU) instead of failing the chat as 500.
- Keep **at most one** listen wav in the prompt so a second listen does not 400.

Those stop crashes. They do not teach the model to open the slide book when the question *sounds* like speech.

A later pass added two loop notes (no keyword list): spoken-word hits are only speech — try another move, and do not search speech again; sound hits are times to listen, not a clap count. **M3 and H2 then passed.** Details: [spoken words, then stop](live-spoken-words.md).
