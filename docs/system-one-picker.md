# System One picker (first-hop routing)

The [thinking experiment is closed](e4b-thinking.md). Default brain stays **Gemma 4 E4B** filling JSON. This note is the opposite experiment: skip JSON **decode** on the first text hop by scoring a closed set of search-book letters from logits.

The picker only chooses **which phone book to open**. Gemma still **looks**, **listens**, and **writes** the answer. Ingest is unchanged.

**Verdict:** picker **stays off** as default. Live `PICKER=shadow` then `PICKER=logit` on the leftover suite did **not** fix H7 / M1 / H5. Committing the sound book on H7 **regressed** listen-then-export. Keep the wiring; do not turn it on in `.env`.

Related: [E4B thinking](e4b-thinking.md) · [hidden-intent questions](live-intent-questions.md) · [architecture](05-architecture.md)

---

## What this is

Gemma's JSON form is a long generated string (`{"do":"search_audio",...}`). That uses **decode**: one token after another.

A System One / Jev-style Choice is a short menu:

```
A. Spoken words
B. Pictures
C. Sounds
D. Slides
E. None of these (look / listen / answer)
```

vLLM runs **one** forward pass, `max_tokens=1`, `logprobs=true`, `top_logprobs=20`. We read the log-probability of each letter, run **softmax**, and take the winner if `p_max ≥ 0.55`.

That is **not** TypeSafe Jev (no unpublished RLCD, no hosted Choice API). Same idea: closed set, parallel scores, no JSON.

Thinking (`GEMMA_THINKING`) is extra decode. The picker skips decode. Chat **does not mix** them: `thinking: true` turns the picker off for that request.

## What it must not do

| Move | Who |
|---|---|
| `search` / `search_visual` / `search_audio` / `search_slides` | Picker **may** fire on hop 1 |
| `look` / `listen` | Always Gemma JSON (needs times + pixels/wav) |
| `export_*` | Always Gemma JSON (needs a range) |
| `answer` | Always Gemma JSON (writing) |
| Follow-up with last times | JSON (the last windows are already in the prompt) |
| Force-answer / hop 2+ | JSON |
| Index not `ready` | That letter is omitted from the menu |

`query` for a picker search is the **user question**. Hit times still come from the index, not from the picker.

If `p_max` is below **0.55**, or the winner is abstain / look / listen / answer, or the GPU errors, the existing JSON brain chooses the first move.

## How to turn it on

Default **off**. Same E4B worker as JSON (`modal_brain.py`). No second replica. No `--reasoning-parser`.

| `PICKER` | What happens |
|---|---|
| `off` (default) | JSON brain for every hop. Chat `picker` is `null`. |
| `fake` | Tests inject `FakePicker`. Production `build_picker` still returns `None`. |
| `logit` | Score letters, **commit** if confident. |
| `shadow` | Score letters, **do not commit**. JSON still acts. Compare `picker.do` vs `steps[0].do`. |

```bash
# gitignored backend/.env
PICKER=shadow          # watch without changing behavior
# or
PICKER=logit
PICKER_MIN_P=0.55
BRAIN=vllm
VLLM_BASE_URL=https://<workspace>--agentic-video-brain-server.<region>.modal.direct/v1
```

Empty `VLLM_BASE_URL` with `PICKER=logit` or `shadow` → HTTP **503**.

Live suite (FastAPI already has `PICKER` set):

```bash
cd backend
BRAIN_LABEL=e4b-picker OUT=/tmp/hidden-intent-e4b-picker.json \
  uv run python eval/run_hidden_intent_suite.py
```

The chat JSON grows `picker: { letter, do, p_max, used, reason, probs }`. The website does not show it.

## Softmax (plain words)

Each letter gets a logit (a raw score). Softmax turns those into numbers that **add to 1**.

If spoken-words is `0.81` and pictures is `0.12`, we are 81% on speech. That is **not** “the answer is 81%.” It is “this is the first book to open,” and only if that 81% clears 0.55.

Calibration (ECE) is **not** measured here. The 0.55 cutoff is a safety rail, not a scientific claim.

## What CI proved

Black mp4s. FakePicker / mocked OpenAI. No Modal GPU in this pass.

`uv run pytest`: **199 passed** (including **21** picker tests).

- Softmax is a distribution; SentencePiece `▁A` counts as `A`.
- Only **ready** books appear, plus abstain.
- Commit / low confidence / abstain / look / shadow / GPU error all behave.
- A committed `search` uses the user question as `query` and **does not** call FakeBrain for hop 1.
- `search_audio` then JSON `listen` still works.
- Follow-ups with last times, hop 2, and `thinking: true` leave the picker off.
- `POST /videos/{id}/chat` returns `picker: null` by default, and a used decision when a FakePicker is injected.
- `PICKER=logit` with no URL is 503.
- Picker source does not name leftover-suite answers.
- Abstain still goes through the existing “do not answer with no move” bounce; JSON must look/search/listen first unless last times exist.

## Live leftover suite (E4B)

Same eight questions as thinking / 12B. Fresh exam tape `0bdc0566-21f9-4051-a8f7-6d91f46ae3c3` (same 16s recipe). All four indexes `ready`. Crutches still off. Hugging Face token loaded CLAP for query embed; Modal E4B served letters + JSON.

Traces: `backend/eval/results/hidden-intent-e4b-picker-shadow.json` and `hidden-intent-e4b-picker-logit.json`. Compare to `hidden-intent-e4b-off.json` (older upload, same recipe).

Letters were **peaked**, not confused. Typical `p_max` 0.93–1.00. H8 correctly **abstained** (`p≈0.79–0.81` on “none of these”) so the walk still began with `look`.

| Q | Shadow (score only; JSON acts) | Logit (commit if confident) | vs leftover |
|---|---|---|---|
| **E1** Pro cost | **pass.** Picker `search` 0.99, JSON `search`. $99. | **pass.** Committed `search`. $99. | Already a pass. Unchanged. |
| **H1** $99 on red? | **pass.** Picker wanted `search_slides` 0.997; JSON opened **speech** first. | **pass.** Committed **slides**. Named Pricing $99; red has no price. | Trap wording. Not worse. |
| **M3** ship this quarter | **pass.** Picker `search` 1.00, JSON `search`. | **pass.** Committed `search`. | Already a pass. |
| **M4** tone + screen | **partial.** Picker `search_audio` 0.999. Named **RED ALERT** (window start), not Q3. | **partial.** Same first book, same miss. | Same 12B/thinking miss. Picker does not listen. |
| **M1** printed color vs speech | **fail.** Picker `search_slides` 0.999 **agreed** with JSON. Looks; **no speech search.** Yellow $99; “cannot confirm.” | **fail.** Committed slides. `p(search)` ≈ 0.0001. | **Did not fix.** One letter cannot open two books. |
| **H5** claps | **partial.** Picker `search_audio` 1.00. Listened; pointed at hit ranges; did not say zero. | **partial.** Same. Still treats CLAP rows as clap-like. | **Did not fix.** Not a clap detector. |
| **H7** clip the beep | **pass.** Picker wanted `search_audio` 0.93; JSON **looked 10.5–13.5, listened, exported that range.** | **fail.** Committed `search_audio` 0.94 → look 12–15 → **export 12–15, no listen.** | **Regressed.** The leftover is hop 2 (listen before cut). Forcing the sound book first brought back dump-the-window. |
| **H8** walk | **pass.** Picker abstain 0.81. Skip-ahead. Names Pricing, RED ALERT, Q3. | **pass.** Abstain 0.79. Same walk. | Already kept. |

Automated tallies: shadow **5 pass / 2 partial / 1 fail**. logit **4 pass / 2 partial / 2 fail**.

Shadow first-hop **agree** with JSON on 6/8 (E1, M3, M4, M1, H5, H8-as-look). Disagree on H1 (slides vs speech) and H7 (audio vs look). Those two are the only commits that change behavior; H7 is the one that hurt.

Wall time for eight chats: shadow ~257s, logit ~154s. That gap is mostly JSON hop variance (M3 50s vs 21s, H8 70s vs 37s), not a measured decode saving. E1 was 18s shadow vs 12s logit. Do not advertise a production token win from this.

## Why default stays off

Same rule as thinking: do not pay a new path on every chat unless the leftover suite says it helps. The picker is **calibrated enough to pick a book**. The leftover bugs are **not** “wrong first book”:

- **H7** is listen-then-export after a **range** hit. The picker is forbidden to listen or export.
- **M1** needs **two** books. The menu is one letter.
- **H5** needs an ear that does not trust CLAP row labels. Scoring “sounds” first is what JSON already did.

A confident first hop can still be the **failing** hop (M1 slides, H7 audio). Leave `PICKER=off`.
