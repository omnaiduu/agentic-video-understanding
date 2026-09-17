# E4B thinking on/off

The [12B A/B is closed](e4b-vs-12b-plan.md). Default brain stays **Gemma 4 E4B**. This note is the next measurement: native Gemma **thinking**, not another 12B pass.

Thinking will not pin 11.00s and is not a clap detector. The question is whether the **planner** starts listening before it exports (H7) and whether it still guesses claps (H5).

Related: [why 4B is enough](why-4b-is-enough.md) · [hidden-intent questions](live-intent-questions.md)

---

## How the toggle works

Default **off**. Same JSON form (`response_format` json_schema, **no** `tools=`).

Two URLs, not one replica with a flag:

| Path | Worker | Parser |
|---|---|---|
| Thinking **off** | existing `agentic-video-brain` (`modal_brain.py`) | none |
| Thinking **on** | `agentic-video-brain-e4b-thinking` (`modal_brain_thinking.py`) | `--reasoning-parser gemma4` |

Do **not** add the parser to the default E4B process. With thinking off, that flag can silently drop json_schema on E4B ([vLLM #39130](https://github.com/vllm-project/vllm/issues/39130)). The thinking replica always gets `enable_thinking=True` and `max_tokens` 4096. Thoughts land in `message.reasoning`; the move stays in `message.content`. History sent back to Gemma is JSON only.

Watch: checkbox **Thinking** (default off). `POST /videos/{id}/chat` with `thinking: true`. Response includes `thoughts: [{do, text}]`. Details shows each move’s thought. Empty `VLLM_THINKING_BASE_URL` → HTTP 503.

```bash
cd backend
modal deploy modal_brain_thinking.py
# then in gitignored .env:
# VLLM_THINKING_BASE_URL=https://<workspace>--agentic-video-brain-e4b-thinking-server.<region>.modal.direct/v1
```

Sources: [Gemma thinking](https://ai.google.dev/gemma/docs/capabilities/thinking) · [vLLM Gemma 4 recipe](https://docs.vllm.ai/projects/recipes/en/latest/Google/Gemma4.html) · [vLLM reasoning outputs](https://docs.vllm.ai/en/stable/features/reasoning_outputs/) · [vLLM #50938](https://github.com/vllm-project/vllm/issues/50938) (preamble before `<|channel>` can break JSON)

---

## Live scoreboard

Same tape `c1d9beb7-5465-4f47-9d53-2d6b299104b5`, crutches **off**. Thinking stays **off** as default unless on clearly wins H7 without breaking JSON or the easy passes.

| | Thinking off | Thinking on |
|---|---|---|
| Smoke beep-clip | pending | pending |
| Hidden-intent suite | pending | pending |
| H7 listen-then-cut | pending | pending |
| H5 clap count | pending | pending |
| E1 / walk / ship | pending | pending |

Traces: `backend/eval/results/hidden-intent-e4b.json` (off) and `hidden-intent-e4b-thinking.json` (on, after the run).
