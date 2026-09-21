# System One picker — closed experiment

**Status: closed. Architecture reverted.** Chat is the **old loop** again: Gemma fills JSON for every hop, including the first one. There is no `PICKER` env, no `picker.py`, no letter logprobs in the request path, no `picker` field on `POST /videos/{id}/chat`.

This file is the record of what we tried, what we implemented, what we tested, what we realized, and **why we are not shipping it**. Do not put the wiring back because a blog post said System One is 200× faster. Measure against **this** product.

Related: [E4B thinking](e4b-thinking.md) · [hidden-intent questions](live-intent-questions.md) · [leftover issues](live-leftover-issues.md) · [architecture](05-architecture.md) · [what we rejected](04-what-we-rejected.md)

**One-line verdict:** the receptionist (closed-set letter scores) is good at pointing at a filing cabinet. This app’s leftover bugs live **after** that point — look, listen, cut, open a **second** book. Obeying the receptionist on the beep-clip question **regressed** listen-then-export. Extra GPU call, no leftover fixes, not cheaper where we spend money. JSON-only stays.

---

## What this document is for

We spent a stacked PR teaching the loop a Jev-shaped first hop, then running it live on the leftover suite. People hyping TypeSafe / Jev and people reading this repo need different things:

- **Hype** is about millions of tiny software gates (triage, route, score, block a tool) where the answer is **already one of N labels**.
- **This repo** is a video loop whose expensive work is **pixels, wav, and a clip**, and whose leftover failures are **multi-step plans**, not “wrong first book.”

Both can be true. We verified the second with a GPU.

Traces (not loaded by the app; they are lab notes):

- `backend/eval/results/hidden-intent-e4b-picker-shadow.json`
- `backend/eval/results/hidden-intent-e4b-picker-logit.json`

Tape for those two files: `0bdc0566-21f9-4051-a8f7-6d91f46ae3c3` (same 16s exam recipe as `c1d9beb7-…` / `live-test-talk.mp4`). All four indexes were `ready`. Crutches still off (no recut-from-middle, no print-vs-speech bounce, no “if unsure say zero”). Skip-ahead **kept**.

---

## 1. What people mean by Jev / System One

### 1.1 The Kahneman slogan

TypeSafe named the class **System One** after *Thinking, Fast and Slow*. System 1 is fast, pattern-matching, “which bucket is this?” System 2 is slow, deliberate, “write the email / reason through the proof.”

The bet: a lot of “AI in production” is System 1 work that we have been **renting System 2** (a chat LLM) to do. The chat model writes a sentence. Your code parses it. Sometimes the JSON is valid and the **content** is still a made-up tool name.

### 1.2 What Jev the product actually is

Jev (TypeSafe AI, announced 15 September 2026, ~$40M seed) is **not a chatbot**. It does not write replies, code, or summaries. You send:

- **state** — the text (or JSON) to judge
- **questions** — a map of typed questions

You get back **typed answers with probabilities**. Three question types only:

| Type | Plain meaning | Example |
|---|---|---|
| **Choice** | Pick 1 of N options you listed (up to 255) | billing / tech / sales |
| **Score** | Place the state on a 2–10 scale you defined in words | can wait / this week / today |
| **Noul** | Probability that a yes/no is true | “Are they asking for a refund?” → 0.99 |

Their line: unstructured state in, **typed probabilistic decisions** out. A **frontier-intelligence function call**, not a novelist.

They **gave up string generation on purpose**. That is the product, not a missing feature. Official intro: [TypeSafe — Introducing System One Models & Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev).

They also claim a **new stack**: parallel sampler, and training they call **RLCD** (Reinforcement Learning for Calibrated Decisions) so that “0.9” is supposed to mean “usually right,” not “token A was likely.” Weights are **not** open. Hosted API, waitlist, billed on **input** tokens. Third-party write-ups quote ~70–500 ms, on the order of **$0.042 per million input tokens**, output free, and marketing numbers like **~200× faster / ~400× cheaper than an LLM on classification**. Those numbers are **their** classification job, not our look/listen loop.

The name **Jev** is after William Stanley Jevons (efficiency can *increase* demand). The API shape is `POST …/v1/systemone` with `model`, `state`, `questions`.

### 1.3 Why people hype it (this is real, and it is a different job)

For years teams used GPT-4 as a sorting hat:

- Which queue is this ticket?
- Is this tool call dangerous? Block it.
- Is this RAG chunk relevant? Drop it before the expensive model.
- May this draft send, or did it promise a refund we do not do?
- Easy question → small model; hard → Opus.

Then they **parsed a paragraph**. Structured output / JSON schema only fixes **shape**. A valid `{"tool":"delete_everything"}` is still a type-legal disaster if `delete_everything` was never on the menu.

Closed options buy:

1. **Cannot invent a fourth department.** The type **is** the menu.
2. **A probability you can `if` on.** `if confidence < 0.55: human`. An LLM’s “I’m pretty sure” is not a shippable number.
3. **Many questions, one pass.** Intent + urgency + risk in **one** call. Parallel over the menu, not left-to-right token decode of a JSON string.
4. **Cost/speed when you do this on every event** — support firehose, moderation, “should this tool run,” not eight leftover video questions.

Typical architecture they want:

- **Jev** — route, gate, score, filter
- **Your code** — thresholds, math, scissors, indexes
- **An LLM** — only the minority that needs a paragraph
- **A human** — low confidence + high stakes

Jev is the receptionist and the bouncer, **not** the person who looks at the film.

### 1.4 What Jev cannot do (the user’s objection is the feature)

It cannot write custom text. It cannot look at video. It cannot listen. It cannot invent a new option. It cannot pick `start_s` / `end_s`. It cannot export a clip. Input in the public API is **text/JSON**, not frames.

If your product’s hard part **is** writing or seeing, Jev is the wrong primitive. That is us.

---

## 2. Science in plain words: decode vs a closed set

### 2.1 What “decode” means here

Gemma’s JSON form is a **string** generated **one token after another**:

```json
{"do":"search_audio","start_s":null,"end_s":null,"query":"beep",...}
```

Each next token is chosen given all previous tokens. That is **autoregressive decode**. It is how chat models write.

Problems when the “answer” is really a **menu**:

- The first token can lock a bad path (`{` then `"do"` then `"look"` when you needed `"search"`).
- The model can emit a verb that is not in the schema unless you constrain it (we already constrain JSON with vLLM `json_schema`).
- You pay for every token of punctuation even though you only needed “sounds.”

JSON schema already **constrains the form**. It does **not** score A vs B vs C **in parallel**. It still walks left to right.

### 2.2 What a Choice / letter pass is

A System One / Jev-style **Choice** is a short menu:

```
A. Spoken words (what people said)
B. Pictures (silent visual)
C. Sounds (tones, music, effects — not the meaning of speech)
D. On-screen slides (printed headings and numbers)
E. None of these (look / listen / answer)
```

One forward pass. You do **not** generate the JSON. You read how much probability mass sits on each **letter**.

On **open-weight vLLM** (what we had), that looks like:

- `max_tokens=1`
- `logprobs=true`
- `top_logprobs=20`

vLLM returns the sampled token **and** the log-probabilities of the top 20 tokens at that position. We harvest the letters A–E (including SentencePiece `▁A` / space-A). Missing letters get a sentinel logit of **−100** (treated as almost impossible).

That is **not** TypeSafe Jev. No unpublished RLCD. No hosted Choice API. No parallel sampler of theirs. Same **idea**: closed set, scores, no essay.

### 2.3 Softmax (plain words)

A **logit** is a raw score, any real number. **Softmax** turns a list of logits into numbers that **add to 1** (a distribution).

If spoken-words is 0.81 and pictures is 0.12, we are 81% on speech as **the first book to open**. That is **not** “the answer to the user is 81% true.” It is not “$99 is 81% correct.” It is only a book choice.

**Calibration (ECE)** was **not** measured. The 0.55 cutoff we used was a **safety rail**: below that, ignore the picker and let JSON act. It is not a scientific claim that 0.55 is well-calibrated on Gemma.

### 2.4 Why skipping decode can look efficient (and when it isn’t)

**The claim:** hop 1 without a picker = Gemma **writes** a JSON move, maybe a few dozen tokens. Hop 1 with a picker = one forward pass, **one** output token, read letter scores. Receptionist cheaper than dictating a form — **if** hop 1 was going to be “open this book,” and **if** you skip that JSON.

**Why that is not a win in this app:**

Almost all cost is **after** the choice:

- **Look** = cut JPEGs, stuff pictures into the next prompt. That dwarfs a short JSON line.
- **Listen** = cut wav, send audio.
- **Answer** = write the sentence.

A letter picker is **forbidden** to do any of that. You still pay the expensive turns.

You also **add** a Modal round trip (picker prompt + `top_logprobs=20`). If the picker says “none of these” (walk the tape), that call is **pure extra**. Then Gemma still writes JSON for `look 0–2`.

If it opens the **failing** plan (beep clip → sound book first), you can spend **more** hops, not fewer. That is what happened when we obeyed it.

JSON schema already makes hop-1 `search` a **short, valid** object. We do not parse free prose. The “stop using a novelist as a sorting hat” pitch is aimed at teams who still parse chat. We already own the form.

---

## 3. Why we tried it **here** anyway

Stacked PRs already closed two experiments:

- **12B vs E4B** — 12B won listen-then-export on H7 once; clap counting got worse; default stayed E4B. [e4b-vs-12b-plan.md](e4b-vs-12b-plan.md)
- **E4B thinking** — extra decode, second GPU worker. H7 not reliable; H5 worse. Default stayed thinking **off**. [e4b-thinking.md](e4b-thinking.md)

The leftover bugs that kept repeating:

| Id | Question in English | What actually fails |
|---|---|---|
| **H8** | Walk the whole tape | **Already fixed** in the laptop (skip-ahead). Not a picker job. |
| **H7** | Clip when the beep happens | Sound search returns a **range**. Planner **exports without listening**. |
| **M1** | Printed number color vs “they said” | Opens **slides**, looks, **never searches speech**. Needs **two** books. |
| **H5** | How many claps? | Treats CLAP **hit rows** as a count / hears claps that are not there. Tape has **zero**. |
| **M4** | When is the tone, what’s on screen | Opens sounds (right book), names **RED ALERT** (window start), not Q3 at ~11s. |
| **H1** | Is $99 on the red emergency screen? | Trap wording. Needs pixels, not a clever first letter. |

A reasonable hypothesis: maybe hop 1 is the wrong **book**, and a closed menu would pick better than JSON. If hop 1 is cheaper and righter, leftover might move.

That hypothesis is what we tested. It was **false** for H7 / M1 / H5. Hop 1 was often **already** the book JSON would have opened. The failures are hop 2+.

---

## 4. What we implemented (now deleted from the loop)

Code lived on `feature/system-one-picker-23a2` stacked on the thinking branch. Default was **off** the whole time. Website never showed the field.

### 4.1 Files (gone from the running architecture)

| Piece | What it did |
|---|---|
| `backend/app/agent/picker.py` | Softmax, letter tokens, `FakePicker`, `LogitPicker`, `routing_options`, `decide_picker`, `picker_allowed` |
| `backend/app/agent/loop.py` | First text hop: score picker; if commit, `BrainAction(do=search_*, query=user question)` with **no times** |
| `backend/app/routes/chat.py` | `get_picker`, `ChatOut.picker` |
| `backend/app/settings.py` | `picker`, `picker_min_p` |
| `backend/tests/test_picker.py` | 21 tests, no GPU |
| env | `PICKER=off\|fake\|logit\|shadow`, `PICKER_MIN_P=0.55` |

`query` for a committed search was **always the user question**. Hit times still came from the **index**, never from the picker.

### 4.2 Modes

| `PICKER` | What happened |
|---|---|
| `off` (default) | JSON brain for every hop. Chat `picker` was `null`. **This is the product again.** |
| `fake` | Tests injected `FakePicker`. Production `build_picker` still returned `None`. |
| `logit` | Score letters, **commit** if confident. |
| `shadow` | Score letters, **do not commit**. JSON still acted. Compare `picker.do` vs `steps[0].do`. |

Empty `VLLM_BASE_URL` with `logit` / `shadow` → HTTP **503**.

Thinking (`GEMMA_THINKING` / `ChatIn.thinking=true`) **turned the picker off** for that request. Extra decode vs skip-decode are opposite bets; we did not mix them.

### 4.3 Hard rules (locked while it existed)

| Move | Who was allowed |
|---|---|
| `search` / `search_visual` / `search_audio` / `search_slides` | Picker **may** fire on hop 1 only |
| `look` / `listen` | **Always** Gemma JSON (needs times + pixels/wav) |
| `export_*` | **Always** Gemma JSON (needs a range) |
| `answer` | **Always** Gemma JSON (writing) |
| Follow-up with last times | JSON (windows already in the prompt) |
| Force-answer / hop 2+ | JSON |
| Index not `ready` | That letter **omitted** from the menu |
| Media already in the last user message | Picker off (not a text-only hop) |

If `p_max` < **0.55**, or the winner was abstain / look / listen / answer, or the GPU errored, JSON chose the first move.

Abstain still hit the existing empty-move bounce: JSON must look/search/listen before answering unless last times exist. We had to fix three tests for that bounce after wiring.

### 4.4 Who decides the **time** to look (this confused us in review)

**The picker never picks a clock.** It has no `start_s` / `end_s`.

Three actors:

1. **Picker** (when logit committed) — “open sounds / slides / speech / none.” No seconds.
2. **The phone book (index)** — after search, hit times. Speech might say `0.00`. Slides `0, 6, 10`. Sounds a **range** like `9–12` or `10.5–13.5`. Those numbers are Whisper / SigLIP / CLAP / ColQwen, not the picker.
3. **Gemma JSON** — **always** the one who says `look` / `listen` / `export` with `start_s` and `end_s`.
4. **Laptop** — scissors, 12-photo cap, skip-ahead, “already looked at this slide time.”

If the picker is off, or it abstains: Gemma JSON decides look times from the first move. That is H8 (walk): abstain → look `0–2`, skip-ahead, etc.

Obeying the picker on the beep clip: hop 1 was search with **no times** → CLAP returned a range → Gemma JSON then chose look `12–15` and exported **without listening**. The picker did not choose 12–15. Gemma did, after reading the hit list.

### 4.5 Letter harvesting details

- Gemma SentencePiece can emit `▁A` (underscore-box A) instead of `A`. We treated that as `A`.
- We scored the **distribution**, not only the sampled string. Sampling `E` while A still has mass is possible; we used softmax over harvested letter logits, not “whatever token came out.”
- An unconstrained smoke (no menu, just “reply with a letter”) once sampled **E (abstain)** at high probability on “How much does Pro cost?” The **real** picker prompt with A–E labels did **not** do that: live E1 was **A / search** at ~0.99. The menu matters.
- Picker source was forbidden to name leftover-suite answers (`$99`, beep at 11s, etc.). Tests grepped for that.

---

## 5. What CI proved (before revert)

Black mp4s. FakePicker / mocked OpenAI. **No Modal GPU** in pytest.

While the wiring existed: `uv run pytest` **199 passed**, including **21** picker tests.

Those tests proved **plumbing**, not leftover quality:

- Softmax is a distribution; `▁A` counts as `A`.
- Only **ready** books appear, plus abstain.
- Commit / low confidence / abstain / look / shadow / GPU error all behave.
- A committed `search` uses the user question as `query` and does **not** call FakeBrain for hop 1.
- `search_audio` then JSON `listen` still works.
- Follow-ups with last times, hop 2, and `thinking: true` leave the picker off.
- Chat default `picker: null`; FakePicker injection returns a used decision.
- `PICKER=logit` with no URL is 503.
- Empty-move bounce still applies after abstain.

After revert, those 21 tests are **gone** with the module. The loop tests that existed before the experiment remain.

---

## 6. Live leftover suite (the thing that decided the product)

### 6.1 Setup

- Brain: live Modal **Gemma 4 E4B** (`google/gemma-4-E4B-it`) at `…--agentic-video-brain-server…/v1`
- Ingest: Modal; query embedders E5 + CLAP + ColQwen (visual query embedder was **fake** to save RAM; look still uses real frames)
- Hugging Face token loaded CLAP (`.bin` + torch ≥ 2.6 on this VM); Modal tokens for GPU; ingest secret for the tunnel
- FastAPI local `:8000`; Cloudflare tunnel for ingest callbacks
- Same eight questions as thinking / 12B (`backend/eval/hidden_intent.py`)
- `PICKER=shadow` first, then `PICKER=logit`, restart uvicorn between (Settings are cached)

### 6.2 Headline tallies

| Mode | Pass | Partial | Fail |
|---|---|---|---|
| Shadow (vote only; JSON still acts) | **5** | **2** | **1** |
| Logit (obey if `p_max` ≥ 0.55) | **4** | **2** | **2** |

Shadow is “JSON as usual, but we wrote down the receptionist’s finger.” Logit is “unlock the cabinet the finger points at.” **Logit scored worse**, because of H7.

Letters were **peaked**, not confused. Typical `p_max` **0.93–1.00**. H8 correctly **abstained** (~0.79–0.81 on “none of these”). The chooser **works**. The leftover bugs are **not** “it can’t pick a letter.”

### 6.3 Shadow: picker vs JSON first move

| Q | Verdict | Picker first book | JSON first move | Agree? |
|---|---|---|---|---|
| **E1** How much does Pro cost? | pass | search 0.99 | search | yes |
| **H1** $99 on the red screen? | pass | search_slides 0.997 | search | **no** |
| **M3** What to ship this quarter? | pass | search 1.00 | search | yes |
| **M4** Tone + what’s on screen | **partial** | search_audio 0.999 | search_audio | yes |
| **M1** Printed color vs speech | **fail** | search_slides 0.999 | search_slides | yes |
| **H5** How many claps? | **partial** | search_audio 1.00 | search_audio | yes |
| **H7** Clip the beep | **pass** | search_audio 0.93 | **look** 10.5–13.5, then listen, export | **no** |
| **H8** Walk the tape | pass | abstain 0.81 | look | yes (abstain → JSON look) |

Agree on 6/8. Disagree on H1 (slides vs speech) and H7 (audio vs look). Those two are the only commits that **change** behavior. H7 is the one that **hurt**.

### 6.4 Logit: what committing did

| Q | Verdict | Committed? | What happened |
|---|---|---|---|
| **E1** | pass | search | $99 |
| **H1** | pass | search_slides | Named Pricing $99; red has no price |
| **M3** | pass | search | Ship the slide index |
| **M4** | partial | search_audio | Named **RED ALERT**, not Q3 |
| **M1** | **fail** | search_slides | Yellow $99; **no speech search**. `p(search)` ≈ 0.0001 |
| **H5** | partial | search_audio | Listened; did not say zero; still clap-like hits |
| **H7** | **fail** | search_audio | look 12–15 → **export 12–15, no listen** |
| **H8** | pass | abstain | Skip-ahead walk still names Pricing / RED ALERT / Q3 |

### 6.5 The beep clip (H7) — the result that matters

**What we want:** find the beep → **listen** to that bit → cut **what you just heard**.

**Watch-only (shadow):** Gemma skipped the sound cabinet at first. Looked **10.5–13.5**, **listened**, exported that window. `listened_before_export=true`. **Pass.** The receptionist, watching, said “open sounds” at 93%. We ignored it.

**Obey (logit):** forced **sound search** (first hit 10.5–13.5) → look 12–15 → **export without listening**. `listened_before_export=false`. **Fail.**

The receptionist was “right” that this is a sound question. Obeying that finger **put us back on the old leftover path** (dump a CLAP-related window, never hear the wav).

The leftover was never “it didn’t know to use the sound cabinet.” The leftover is hop 2: **listen, then cut.** The picker is not allowed to listen or export. Forcing hop 1 to search_audio **removes** the lucky JSON path that looked near 11s first.

This matches earlier E4B-off history (export without listen) and why 12B / thinking were interesting: they sometimes **listened**. A letter menu cannot.

### 6.6 Printed vs speech (M1)

Needs **two** cabinets: slides (yellow `$99`) **and** spoken words. Then “they match.”

The picker can only point at **one** letter. It pointed at **slides** at 99.9%. Speech got ~0.01%. Gemma looked, saw yellow `$99`, hedged: cannot confirm a match.

Shadow JSON did the **same** first hop. Obeying did not help. One finger cannot mean “open both.” The old print-vs-speech **bounce** (block answer until `search`) was exam-shaped and **stays removed**.

### 6.7 Claps (H5)

Tape has **zero** claps. Picker correctly said sounds (~100%). JSON already did that. Then it treated search hits as clappy-ish and did not say zero. Scorer: **partial** (listened, no numeric five, no word zero). Not a clap detector. Letter scores cannot hear.

### 6.8 Tone + screen (M4)

Right first book (sounds). Hit is a **window**; start is still RED ALERT; beep is later on Q3. Named the red slide. **Partial.** Picker cannot look or listen to finish the question.

### 6.9 Walk (H8)

Already fixed by **skip-ahead** in the laptop. Picker abstained. Walk still named Pricing, RED ALERT, Q3. **Pass.** Do not credit the picker for H8.

### 6.10 Easy questions (E1, M3) and the trap (H1)

Pro cost and ship-this-quarter stayed passes. Picker and JSON agreed on speech first.

H1 (false premise: $99 on red): shadow JSON opened **speech** first and still passed the scorer; logit committed **slides** and passed more clearly (price on Pricing, red has no dollar). That is a possible micro-win on trap wording. It does not pay for H7 regression or an extra call on every chat.

### 6.11 Wall clock (do not advertise)

Eight chats: shadow ~**257s**, logit ~**154s**. The gap is mostly JSON taking different paths (M3 50s vs 21s, H8 70s vs 37s), not “letters are faster than JSON.” E1 was 18s vs 12s. **Do not** treat this as a production token win.

### 6.12 Compared with earlier leftover columns

| Leftover | E4B JSON (typical) | 12B | Thinking on | Picker logit |
|---|---|---|---|---|
| H8 walk | pass (skip-ahead) | pass | pass | pass (abstain) |
| H7 beep clip | often fail (no listen) | pass (listen then cut) | suite pass, smoke fail | **fail** (forced sound → no listen) |
| M1 two books | fail (slides only) | partial (opened both) | partial | **fail** (slides only, worse certainty) |
| H5 claps | partial / invent | worse (five claps) | worse (heard claps) | partial (not zero) |
| M4 tone+screen | sometimes pass | partial (RED ALERT) | partial | partial |

Picker logit did **not** beat JSON E4B on the leftovers we still care about. It **lost** H7 relative to **this same tape’s** shadow JSON run.

---

## 7. What we realized (the actual lessons)

1. **Closed-set routing is a real primitive** for classify / choose / score. TypeSafe’s hype is aimed at that. We are not that product.

2. **Our leftover bugs are not “wrong first book.”** They are listen-before-export, two books, an ear that does not trust CLAP rows, naming the slide **at the tone** not at the window start.

3. **A confident first hop can be the start of the failing plan.** M1 slides at 99.9% and H7 audio at 93% were sharp **and** harmful or useless.

4. **The picker cannot have a clock.** People asked “who decides the time to look, now that we have a smart picker?” **Gemma JSON still does.** Indexes propose times. The laptop cuts. If you wanted the picker to choose 11.00s, you would be hardcoding the exam tape. We refuse that.

5. **Skipping decode is not efficiency here.** Look/listen dominate. Extra logprob call is extra. Abstain is wasted. Wrong commit can add hops.

6. **JSON schema already did the “don’t emit garbage verbs” job** for hop 1. We did not need a second brain for valid `search_*`.

7. **Do not restore crutches** (recut-from-middle, print-vs-speech bounce, say-zero) because a letter menu failed. Those crutches were exam-shaped. The honest next steps for leftovers remain detectors / planner quality / architecture, **not** a receptionist.

8. **Thinking and picker are opposite knobs.** Thinking = more decode. Picker = skip decode on hop 1. Mixing them was correctly forbidden. Neither is the default.

9. **Open-weight logprobs ≠ Jev.** Same shape, different model, no RLCD, no parallel multi-question API, no calibrated “0.9.” We must not advertise Gemma letters as TypeSafe.

10. **Shadow then logit is the right way to kill an idea.** Shadow showed the finger was peaked and often agreed with JSON. Logit showed the two disagreements: one harmless (H1), one a regression (H7). That is enough to revert.

---

## 8. Why we revert to the old approach

**Old approach (the product):**

User question → FastAPI → Python loop → Gemma fills **JSON** (`look` / `listen` / `search_*` / `export_*` / `answer`) → laptop runs the move → attach photos/wav as content parts → repeat → answer.

**What we are not choosing:**

A second hop-0 path that scores A–E from logprobs and may replace hop 1 JSON with a search that has no times.

**Why:**

- Live leftover suite: **worse** when obeyed (4/2/2 vs 5/2/1).
- H7 listen-then-export **regressed**.
- M1 / H5 / M4 **unfixed**.
- H8 already belonged to skip-ahead.
- Efficiency story **did not land**.
- Product surface grew (`PICKER`, `picker` on ChatOut, 21 tests, two modes) for a path we would leave **off** forever. Dead wiring is how crutches come back.

Revert means **delete the path**, not “leave it off in `.env`.” Off-but-wired is how someone turns logit on in a live `.env` and ships the H7 failure.

---

## 9. What the repo looks like after revert

**Removed from runtime:**

- `backend/app/agent/picker.py`
- `backend/tests/test_picker.py`
- `picker` / `picker_min_p` settings
- `PICKER` / `PICKER_MIN_P` in `.env.example` and READMEs
- loop hook, `ChatOut.picker`, `get_picker`
- architecture diagram line, key-decisions bullet, glossary rows that described it as a live option

**Kept:**

- This file (closed experiment).
- Live traces JSON under `backend/eval/results/hidden-intent-e4b-picker-*.json` (lab notes).
- Pointers from leftover-issues, thinking doc, rejected-ideas table.

**Unchanged (still the product):**

- E4B JSON brain, optional thinking worker **off** by default
- Four indexes, skip-ahead, no recut / print-bounce / say-zero
- Website Watch checkbox for thinking only

---

## 10. How to read this if you only remember the hype

> “Can it write custom text?” **No.** That is Jev’s design. We still need Gemma to write answers and to look.

> “So it’s just classification?” **Yes.** Choose from options you already wrote. Score. Yes/no probability.

> “Why is that better than an LLM?” **When the job is a gate in software**, a type plus a probability beats a paragraph you parse. **When the job is a video loop**, you still need the novelist-with-eyes. We already constrain JSON. The leftover work is the plan after the first verb.

> “Did we prove letters don’t work?” **No.** We proved letters **do** work as a book chooser on this tape, and that **this product does not need that chooser**.

---

## 11. Sources (Jev product claims)

- [TypeSafe — Introducing System One Models & Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev)
- [Jev explained (System One Models)](https://systemonemodels.org/guides/jev-explained/)
- [LangChain — building a harness with Jev](https://www.langchain.com/blog/building-a-harness-with-jev)
- [Apidog — decision layer, not another chatbot](https://apidog.com/blog/how-to-use-jev/)

Our live numbers are **ours** (eval JSON), not TypeSafe’s 200× claim.
