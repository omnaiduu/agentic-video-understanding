# E4B vs Gemma 4 12B Unified — A/B

Default brain stays **Gemma 4 E4B** (`google/gemma-4-E4B-it`). This file is the 12B task: a **second** Modal worker, the **same hidden-intent questions**, and a scorer. Crutches stay **off**. Skip-ahead stays.

Confirmed Hugging Face id: [`google/gemma-4-12B-it`](https://huggingface.co/google/gemma-4-12B-it) (instruction-tuned Unified, text + image + audio). Do not pick 31B / 26B-A4B (no audio).

Related: [why 4B is enough](why-4b-is-enough.md) · [sound windows](sound-window-export.md) · [leftover issues](live-leftover-issues.md) · [leftover report](live-leftover-report.md)

---

## What 4B failed that 12B will be tested on (no prompt crutches)

This is the whole point of the A/B. **Do not put the prompt/bounce crutches back.** Run 12B on the **clean loop** (skip-ahead stays; recut / print-vs-speech / “say zero” are gone). Same eight questions in `backend/eval/hidden_intent.py`. Same 16s tape.

E4B **could not do these on its own**. Those are the 12B tests:

| Q | What 4B did *before* the prompt crutches | What 12B must do without those crutches |
|---|---|---|
| **H7** clip when the beep happens | `search_audio` returned a 9–12s **range**. E4B **exported 9–12 with no listen**. Clip mixed the previous slide (red) with the tone. | **Listen first**, then export **only the range it heard**. Pass = `listen` before `export_clip`, and the cut is not the raw CLAP window unless that is what it heard. Script flag: `listened_before_export`. |
| **M1** printed number color, match speech? | Looked at the pixels (yellow $99). **Answered without `search`.** “Cannot confirm it matches.” | Open **both** books on its own: look at the printed number **and** search speech, then say match / no match. Script flag: `searched_speech`. |
| **H5** how many claps? | Treated CLAP **hit rows** as a count, or listened to silence/tone and said **one clap**. This tape has **zero** claps. | Listen at a hit. If the wav is not claps, say **zero**. Still no laptop clap detector. |
| **H1** is $99 on red? | Unstable. Sometimes named navy/yellow correctly; sometimes led with **Yes** (the trap). No laptop rule existed. | Reject the false premise from the pixels. Do not add a “say no” bounce. |
| **M4** tone + on screen? | Worked only after a note that said **look/cut at the middle** of the CLAP window. | Listen inside the hit, then say what is on screen. `middle=` is information, not a command. |

**Not a 12B test of “smarter prompting.”** These crutches stay **off** for the A/B (they are what 4B needed, and what we are measuring 12B against):

- Recut-from-middle (~2s from the CLAP midpoint) + bounce answers until that recut + extra-export cap. That is how H7 “passed” on E4B.
- Keyword bounce: block `answer` until `search` if the question has `printed` + `they said`. That is how M1 “passed” on E4B.
- “If unsure, say zero” clap bounce. Exam-shaped; already removed.

**Not a 12B vs 4B gap (keep as-is):**

- **H8** walk the tape: 4B crawled 2s steps and burned 12 moves. **Skip-ahead stays** — that is loop hygiene, not a prompt guess.
- **E1** Pro cost and **M3** ship this quarter: 4B already passed without a crutch. 12B must not regress.

If 12B still dumps the CLAP window or still skips speech, write **12B still failed H7 / M1**. Next step is a detector or architecture, **not** restoring the crutches.

---

## Why prompting was fragile

The laptop owns the loop. Gemma only fills JSON. When E4B picked a weak plan, we appended **user notes** and sometimes **refused `answer`** until it obeyed.

That works until it does not:

- Notes compete with 12 JPEG parts, one wav, and the system prompt. E4B often **ignored** them (H5 “times to listen, not a count” still became “one clap”).
- Keyword gates (`printed` + `they said` → force `search`) pass **this wording** and miss the next phrasing (“is the number on the slide the same as the voiceover?”).
- Recut-from-middle **guesses** the event at the CLAP midpoint. That matched one 16s tape. It is not hearing.
- Each bounce burns a round toward the 12-move cap. Extra gates made H7 walk off the end of the file (11.5–16 death spiral) until we added *another* gate.

Official card, Tau2 tool-use (average of 3): **E4B 42.2%** vs **12B Unified 69.0%**. We do not use native `tools=`, but the leftover fails are the same skill: **multi-step plan** (open the right book, listen, then cut / compare). 12B also scores higher on vision (MMMU Pro 69.1 vs 52.6) and has a 256K context window vs 128K (we still cap the prompt; this is about planner quality, not dumping the file).

So the hypothesis is: **E4B needed the crutches; 12B might not.** The A/B is how we find out instead of prompting harder.

---

## What E4B actually failed (same eight questions)

Live Modal, tape `c1d9beb7-5465-4f47-9d53-2d6b299104b5`, Gemma 4 E4B, HTTP 200 unless noted. Catalog: `backend/eval/hidden_intent.py`.

| Q | Ask (short) | E4B without the crutch | Crutch we used | Crutch now |
|---|---|---|---|---|
| **E1** | Pro cost? | Pass. Speech → $99. | none | none |
| **H1** | $99 on red? | Unstable. Sometimes “not on red,” sometimes leads with Yes. | none | none |
| **M3** | Ship this quarter? | Pass. Leave speech, slides, look at Q3. | none | none |
| **M4** | Tone + on screen? | Pass after a “look near the middle” hint. | middle= + “cut from the middle” in the observe note | Observe says **listen**, then describe. `middle=` is still printed as a number, not a command. |
| **M1** | Printed number color, match speech? | Looked at the pixels; answered without `search`; “cannot confirm.” | Block answer until speech search; then “compare the lines.” Live pass only **with** that bounce. | **Removed.** 12B should open both books. |
| **H5** | How many claps? | Invented claps from hit rows or from silence/tone. | “If unsure, say zero” (exam-shaped). | **Already removed.** No clap detector. |
| **H7** | Clip when the beep happens. | Exported the **whole 9–12s CLAP range**, no listen. | Recut from middle ~2s; bounce answers; cap extra exports. Live pass only **with** recut. | **Removed.** OG: listen, export what you heard. |
| **H8** | Walk the whole tape. | 2s crawl burned 12 moves by ~9s. | Skip the next 2s step when >6s remain (look-only too). Live pass. | **Kept.** Loop hygiene, not a content guess. |

H7 and M1 are the A/B. H5 is “needs a detector or a model that trusts its ear.” H1 is trap wording. H8 is already a general skip rule.

Nothing in this table is an answer key for times (no “if they say beep, jump to 11s”).

---

## What 12B is

| | **E4B (today)** | **12B Unified (this plan)** |
|---|---|---|
| Hugging Face id | `google/gemma-4-E4B-it` | **`google/gemma-4-12B-it`** ([HF card](https://huggingface.co/google/gemma-4-12B-it), confirmed) |
| Weights this L4 loads | same as the served id | Official QAT [`google/gemma-4-12B-it-qat-w4a16-ct`](https://huggingface.co/google/gemma-4-12B-it-qat-w4a16-ct) (~8.3 GB). Served **as** `google/gemma-4-12B-it`. BF16 12B is ~23 GB weights; vLLM’s server recipe wants ~40 GB+ in BF16. The [16 GB laptop figure](https://blog.google/innovation-and-ai/technology/developers-tools/introducing-gemma-4-12b/) is on-device, not a BF16 vLLM replica. |
| Modalities | text + image + audio | text + image + audio (encoder-free Unified) |
| Do **not** pick | — | 31B / 26B-A4B: **no audio** |
| Tau2 | ~42% | ~69% |
| GPU | L4 24 GB | L4 24 GB (QAT). Same card as E4B. |
| vLLM | `vllm[audio]==0.29.0`, JSON schema, image 64 / audio 1, `max-model-len` 8192 | **same flags**. No `tools=`, no `--reasoning-parser`. If this OOMs, lower image cap or util — do not raise 12 loop rounds. |

We still **own the JSON loop**. 12B still does not call `tools=`. Same FastAPI, same four books, same scissors.

“Extra search” here means **the same four indexes**, not a new web-search tool and not 31B HLE-with-search.

---

## What we implemented (this PR)

Do not add the recut / print-vs-speech bounces back if 12B fails; record the fail.

1. **Id confirmed.** `google/gemma-4-12B-it`. Same gated Gemma access; Modal secret `huggingface`.
2. **Second app, E4B left up.** `backend/modal_brain_12b.py`, Modal app `agentic-video-brain-12b`. `modal_brain.py` still serves E4B as `agentic-video-brain`.
3. **Served name** `google/gemma-4-12B-it`. **Weights** `google/gemma-4-12B-it-qat-w4a16-ct` (L4). Same image (`vllm[audio]==0.29.0`), same L4, same HF/vLLM volumes, same `json_schema` from `VllmBrain`. The 12B image applies `modal_patches/patch_gemma4_unified_audio_dummy.py` because vLLM 0.29 dummy-audio profiling still reads tower `fft_length`; Unified 12B does not have that attribute. E4B is unpatched.
4. **Deploy:** `cd backend && modal deploy modal_brain_12b.py`. Then:

   ```bash
   VLLM_BASE_URL=https://<12b-worker>/v1 uv run python eval/wait_vllm.py
   ```

5. **Point FastAPI only** (gitignored `.env`, or a second uvicorn on another port so E4B stays on 8000):

   ```bash
   BRAIN=vllm \
   VLLM_BASE_URL=https://<12b-worker>/v1 \
   VLLM_MODEL=google/gemma-4-12B-it \
     uv run uvicorn app.main:app --host 127.0.0.1 --port 8001
   ```

   Restart **without** assuming `--reload`. Do not commit `.env`. Default in `settings.py` stays E4B.

6. **Same tape.** `c1d9beb7-5465-4f47-9d53-2d6b299104b5` when indexes are `ready`. Do not bake those times into loop code.

7. **Same questions:**

   ```bash
   VIDEO_ID=c1d9beb7-5465-4f47-9d53-2d6b299104b5 \
   BASE_URL=http://127.0.0.1:8001 BRAIN_LABEL=12b \
   VLLM_MODEL=google/gemma-4-12B-it \
   OUT=/tmp/hidden-intent-12b.json \
     uv run python eval/run_hidden_intent_suite.py
   ```

   Then the same command with `BRAIN_LABEL=e4b` against the E4B FastAPI so the traces sit side by side. Fresh chat session per question.

8. **Score steps, not the observe note.** `eval/score_hidden_intent.py` (also printed at the end of the runner):

   | Q | 12B looks better if… | Script flags |
   |---|---|---|
   | **H7** | `listen` before `export_clip`. Cut is the heard range, not the raw CLAP hit unless that is what it heard. | `listened_before_export`, `exported_heard_range`, `dumped_unheard_clap_window` |
   | **M1** | Speech `search` **and** a look. Names a color; says match / no match. | `searched_speech` |
   | **H5** | After a listen, does not invent claps from hit-row count. Zero is allowed. | — |
   | **H8** | Names Pricing, RED ALERT, Q3. Skip-ahead may still fire. | — |
   | **E1 / M3 / M4** | Must not regress. | — |

   Pass only on HTTP **200** plus those steps. Do not call H7 a pass because the observe note mentioned `middle=`.

9. **12B column** goes in [leftover issues](live-leftover-issues.md). If 12B still dumps the CLAP window, write **12B still failed H7** — next is a detector or architecture, **not** restoring recut-from-middle.

10. **E4B stays default** in `settings.py` / `.env.example` until someone chooses to switch.

---

## Live scoreboard

Same tape `c1d9beb7-5465-4f47-9d53-2d6b299104b5`, indexes `ready`. Clean loop (skip-ahead on; recut / print-vs-speech / “say zero” off). Fresh chat session per question. All eight HTTP **200** on both brains.

- E4B: existing FastAPI on port 8000 → `agentic-video-brain` (`google/gemma-4-E4B-it`)
- 12B: FastAPI on port 8001 → `agentic-video-brain-12b` serving `google/gemma-4-12B-it` from QAT `google/gemma-4-12B-it-qat-w4a16-ct`

Traces: `backend/eval/results/hidden-intent-e4b.json` and `hidden-intent-12b.json`. Scorer: `eval/score_hidden_intent.py`.

| Q | E4B this run | 12B this run | What that means |
|---|---|---|---|
| **E1** | **pass.** `search` speech. “$99 a month.” | **pass.** Slides + look at Pricing. “$99 per month.” | No regression. |
| **H1** | **pass** (scorer). Leads with “Yes” about speech matching print; also says yellow on **dark blue** at 0s. Looked at red, Pricing, and Q3. | **pass.** Explicit: price is **not** on red; it is on navy Pricing; red is RED ALERT. | 12B is clearer on the trap. E4B still likes to start with Yes. |
| **M3** | **pass.** Speech → slides → look 10s. “Ship the slide index.” | **pass.** Same path. | No regression. |
| **M4** | **pass.** Sound 9–12 → look+listen **10–13**. Names Q3 / Ship the slide index. | **partial.** Sound 9–12 → listen **9–12** + look **9–12**. Names **RED ALERT** (the start of the CLAP window). | 12B listened (good) but described the window start, not the tone. Do not put “cut from the middle” back. |
| **M1** | **pass.** Looks 10, 0, 6, then `search` speech. Yellow $99 matches spoken $99. **No bounce.** | **partial** (scorer). Same path: looks 10, 0, 6, then `search`. Yellow $99; speaker said the number is printed. Did not say the word “match.” | Both opened both books without the keyword bounce. E4B is not *always* skip-speech; historically it was. |
| **H5** | **partial.** Listen 7–9. “Couldn’t clearly hear any claps.” Not the word zero. | **fail.** Listened 6–9, 7.5–10.5, 12–15, 13.5–16. Invented **five claps**. | 12B did **not** fix counting. Still no clap detector. Do not restore “say zero.” |
| **H7** | **fail.** Sound 9–12 → **export 9–12 with no listen**, then a second export 10–12.5. Answer talks about “the middle of the search window.” Flag: `dumped_unheard_clap_window`. | **pass.** Sound 9–12 → **listen 10.5–13.5** → look 10.5–13.5 → **export 10.5–13.5**. Flags: `listened_before_export`, `exported_heard_range`. Real `export_url` is the laptop path. The answer text also hallucinated a GCS mp4 URL — ignore that; the cut is the heard range (Q3 + beep), not 9–12 red+Q3. | **This is the A/B.** 12B did the OG path. E4B still dumped the CLAP range. Crutches stay off. |
| **H8** | **pass.** Skip-ahead blocked 1–2s. Names Pricing, RED ALERT, Q3. | **pass.** Skip-ahead blocked 4–8s. Names Pricing, RED ALERT, Q3 / Ship the slide index. | Skip-ahead is enough. |

Automated tallies (strict scorer): E4B 6 pass / 1 partial / 1 fail. 12B 5 pass / 2 partial / 1 fail. **Do not switch the default brain.** 12B won the leftover that the crutches were faking (H7). It did not win clap count or “what is on screen at the tone.” Next for those is a detector or architecture, not more notes. Plain write-up of the same facts: [why 4B is enough](why-4b-is-enough.md).

Default in `settings.py` remains `google/gemma-4-E4B-it`.

---

## Files

| Piece | Where |
|---|---|
| 12B Modal worker | `backend/modal_brain_12b.py` (app `agentic-video-brain-12b`) |
| Unified audio dummy patch (12B image only) | `backend/modal_patches/patch_gemma4_unified_audio_dummy.py` |
| E4B Modal worker (unchanged default) | `backend/modal_brain.py` |
| HF / app constants | `backend/eval/brains.py` |
| Question list + E4B notes | `backend/eval/hidden_intent.py` |
| Live runner | `backend/eval/run_hidden_intent_suite.py` |
| Scorer | `backend/eval/score_hidden_intent.py` |
| Wait for `/v1/models` | `backend/eval/wait_vllm.py` |
| Live traces (this A/B) | `backend/eval/results/hidden-intent-e4b.json`, `hidden-intent-12b.json` |
| Catalog + scorer tests | `backend/tests/test_hidden_intent.py` |
| OG loop tests | `backend/tests/test_loop_rules.py` |
| Skip-ahead (kept) | `backend/app/agent/loop.py` |
