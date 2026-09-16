# E4B vs Gemma 4 12B Unified — plan (not deployed)

Default brain stays **Gemma 4 E4B** (`google/gemma-4-E4B-it`). This file is the next task: run the **same hidden-intent questions** on **Gemma 4 12B Unified** and see which leftover fails were “small model + fragile prompting” vs real loop/index limits.

**This change does not deploy 12B.** It only:

- Removes the E4B crutches (recut-from-middle, extra-export cap, print-vs-speech bounce).
- Keeps skip-ahead (H8).
- Gives unit tests for the OG listen-then-export path.
- Gives a live suite script with the eight questions E4B already ran.

Related: [sound windows](sound-window-export.md) · [leftover issues](live-leftover-issues.md) · [leftover report](live-leftover-report.md)

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

## What 12B is (confirm on the card before deploy)

| | **E4B (today)** | **12B Unified (this plan)** |
|---|---|---|
| Hugging Face id | `google/gemma-4-E4B-it` | **`google/gemma-4-12B-it`** (instruction-tuned Unified; confirm on [the HF card](https://huggingface.co/google/gemma-4-12B-it) before `modal deploy`) |
| Modalities | text + image + audio | text + image + audio (encoder-free Unified) |
| Do **not** pick | — | 31B / 26B-A4B: **no audio** |
| Tau2 | ~42% | ~69% |
| 4-bit weights | ~4.5 GB | ~6.7 GB |
| GPU | L4 24 GB is enough | L4 24 GB is enough (16 GB min on the 12B blog) |
| vLLM | same JSON schema, `--limit-mm-per-prompt` image 64 / audio 1, `max-model-len` 8192 | **same flags** unless 12B OOMs — then lower image cap or util, do not raise 12 loop rounds as a “fix” |

We still **own the JSON loop**. 12B still does not call `tools=`. Same FastAPI, same four books, same scissors.

“Extra search” here means **the same four indexes**, not a new web-search tool and not 31B HLE-with-search.

---

## Concrete implement steps (future task)

Do these in order. Do not add the recut / print-vs-speech bounces back if 12B fails; record the fail.

1. **Confirm the id.** Open the HF card. If Google renamed the IT checkpoint, use that name. Same gated Gemma access; existing Modal secret `huggingface` should work.

2. **Do not overwrite E4B.** Copy `backend/modal_brain.py` to a second app (suggested: `agentic-video-brain-12b`) **or** add `MODEL_NAME` from env with a different `modal.App` name. Keep the E4B worker up so you can flip FastAPI between URLs.

3. **Set** `MODEL_NAME = "google/gemma-4-12B-it"` (or the confirmed id). Same image (`vllm[audio]==0.29.0`), same L4, same volumes, same `json_schema` on the laptop client (`VllmBrain` already sends `RESPONSE_FORMAT`).

4. **`modal deploy`** that file from `backend/`. Wait until `GET /v1/models` is 200. Cold start can take minutes (weights + snapshot).

5. **Point FastAPI only.** In `backend/.env` (gitignored):
   - `BRAIN=vllm`
   - `VLLM_BASE_URL=https://<12b-worker>/v1`
   - `VLLM_MODEL=google/gemma-4-12B-it`
   Restart uvicorn **without** assuming `--reload`. Do not commit `.env`.

6. **Same tape.** Reuse upload `c1d9beb7-5465-4f47-9d53-2d6b299104b5` if the DB still has it and indexes are `ready`. Otherwise re-upload the same 16s recipe (Pricing / RED ALERT / Q3 + ~11s tone). Do not bake those times into loop code.

7. **Same questions.** From `backend/`:

   ```bash
   VIDEO_ID=<id> BASE_URL=http://127.0.0.1:8000 BRAIN_LABEL=12b \
     OUT=/tmp/hidden-intent-12b.json \
     uv run python eval/run_hidden_intent_suite.py
   ```

   Then the same command with `BRAIN_LABEL=e4b` against the E4B URL so the traces sit side by side. Fresh chat session per question (the script POSTs `/videos/{id}/chat` without `session_id`).

8. **Score the A/B, not the wording of the note.** For each question, compare **steps**:

   | Q | 12B looks better if… |
   |---|---|
   | **H7** | `listen` (ok) **before** `export_clip`. Export is the heard range, not the raw 9–12 hit (unless the listen window *was* 9–12 and that is what it heard). Script field: `listened_before_export`. |
   | **M1** | `search` (speech) **and** a look at Pricing. Script field: `searched_speech`. Names a color; says match / no match from those lines. |
   | **H5** | After a listen, does not invent claps from hit-row count. Zero is allowed if the wav is not claps. |
   | **H8** | Still names Pricing, RED ALERT, Q3. Skip-ahead may still fire; that is fine. |
   | **E1 / M3 / M4** | Must not regress. |

   Pass only on HTTP **200** plus the content/steps above. Do not call H7 a pass because the observe note mentioned `middle=`.

9. **Write the 12B column** into [leftover issues](live-leftover-issues.md) (new scoreboard). If 12B still dumps the CLAP window, document that as **12B still failed H7** — next options are a detector or architecture, **not** restoring recut-from-middle.

10. **Leave E4B as default** in `settings.py` / `.env.example` until the A/B is done and someone chooses to switch.

---

## What this repo already contains for that task

| Piece | Where |
|---|---|
| Question list + E4B notes | `backend/eval/hidden_intent.py` |
| Live runner | `backend/eval/run_hidden_intent_suite.py` |
| Catalog tests | `backend/tests/test_hidden_intent.py` |
| OG loop tests | `backend/tests/test_loop_rules.py` (`search_audio` → listen → export heard range; full-window export is **not** recut; print-vs-speech is **not** blocked) |
| Skip-ahead (kept) | `backend/app/agent/loop.py` `_is_next_step_after_listen` |

Do not implement steps 2–5 in the leftover-crutches PR. That *is* the 12B task.
