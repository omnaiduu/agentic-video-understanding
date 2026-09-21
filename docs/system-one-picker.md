# System One picker (first-hop routing)

The [thinking experiment is closed](e4b-thinking.md). Default brain stays **Gemma 4 E4B** filling JSON. This note is the opposite experiment: skip JSON **decode** on the first text hop by scoring a closed set of search-book letters from logits.

The picker only chooses **which phone book to open**. Gemma still **looks**, **listens**, and **writes** the answer. Ingest is unchanged.

**Verdict:** picker **stays off** as default. Wiring and fallbacks are tested without a GPU. A live `PICKER=logit` pass on the leftover suite is still outstanding.

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

## What we did not prove

No live E4B logit pass on the eight leftover questions. This environment has no Modal GPU. Do not claim H7 / H5 / E1 routing quality until `PICKER=shadow` then `PICKER=logit` run against the exam tape.

Expected live risks (not measured):

- A confident **wrong** book (speech for a slide-only heading).
- Letters missing from `top_logprobs=20` (treated as a very low logit).
- First-token not a letter (`The` / `{`) even though we score the distribution, not the sampled string.

## Why default stays off

Same rule as thinking: do not pay a new path on every chat until the leftover suite says it helps. JSON schema already constrains the form. The picker only saves the **first routing hop**, and only when the question is a book choice. Look/listen/answer still decode.

Start with **shadow** so we can compare `picker.do` to the JSON first move without changing answers.
