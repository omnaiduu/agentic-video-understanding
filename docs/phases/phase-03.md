# Phase 3 — Brain loop

**Status: LOCKED** (structured JSON via vLLM + our state machine). An agent may implement only this file after Phases 1–2.

Depends on: [Phase 1](phase-01.md), [Phase 2](phase-02.md).

Related: [architecture](../05-architecture.md) · [Gemma card](https://ai.google.dev/gemma/docs/core/model_card_4) · [function calling](https://ai.google.dev/gemma/docs/capabilities/text/function-calling-gemma4) · [phase map](../12-build-phases.md)

---

## What we are trying to do

You ask a question. **Our server** decides what happens next. The model only fills in a **JSON form**: look, listen, or answer. We cut the slice (Phase 2). We **show** the photos/sound as normal multimodal input. Repeat. Then we return the answer.

Still no website. Still no search. Best for questions that already have a time (“what happens at 0:10?”).

---

## What we verified (docs + public issues)

**Gemma can see and hear.** E2B, E4B, and 12B take **text + image + audio in**. They only **write text out**. ([model card](https://ai.google.dev/gemma/docs/core/model_card_4))

**Native tool calling is text-in / text-out.** Official examples put **JSON in `tool_responses`** (weather). They do **not** show photos or wavs inside a tool result. ([function calling](https://ai.google.dev/gemma/docs/capabilities/text/function-calling-gemma4))

**Putting images on a `tool` message is broken on many hosts.** Google’s Gemma 4 chat template used to **drop** image/audio parts in tool messages (only kept `type == "text"`). vLLM had to patch this ([PR #41459](https://github.com/vllm-project/vllm/pull/41459), May 2026). Other stacks still split “tool text” and “image in a user message,” and the model **does not see** the picture ([example](https://github.com/badlogic/pi-mono/issues/3022)).

**E4B is multimodal on input, weak as a multi-step tool agent.** Tau2 tool-use: E4B **42.2%** vs 12B **69%**. ([model card](https://ai.google.dev/gemma/docs/core/model_card_4)) So “E4B + native tools + images in tool results” is the worst mix.

**Therefore:** we do **not** ask Gemma to drive OpenAI-style `tools=`. We **own the loop**. Gemma only emits a small JSON action. We attach frames/audio as **user-content image/audio parts** (the path the audio/vision docs actually show).

That matches the product plan: Think → Act → Observe, with **Act in our Python**, not in the host’s tool parser.

---

## Words

**State machine** — our code has states. The model does not “run tools.” It only says what it wants. We do the rest.

**Structured output** — the model must fill a JSON shape we define. Prefer **constrained decoding** (`guided_json` / Outlines) so it cannot wrap JSON in chatter. If the host has no grammar, parse JSON and retry once.

**Look / listen / answer** — the only three moves in Phase 3.

---

## The loop we control

```
state = ASK
rounds = 0

ASK:
  send user question + schema
  model → JSON

BRANCH on JSON.do:
  look    → get_frames (Phase 2 caps) → append photos as image parts → rounds++ → ASK again
  listen  → get_audio  (Phase 2 caps) → append wav as audio part   → rounds++ → ASK again
  answer  → return text + times
  junk / oversize / rounds > 8 → stop with error or best-effort text
```

**JSON shape (proposed)**

```json
{
  "do": "look" | "listen" | "answer",
  "start_s": 10.0,
  "end_s": 14.0,
  "fps": 2,
  "answer": null,
  "times": [10.0]
}
```

- `look` / `listen`: we ignore `answer`. Times must pass Phase 2 caps or we refuse and tell the model “too big, try smaller.”
- `answer`: we return `answer` + `times` to the user.
- Invalid JSON: retry once with “return only the schema”; then fail.

**How Gemma sees the cut:** next message is a **user** turn (or assistant-less multimodal turn) with text “frames at 10.0s, 10.5s, …” **plus** `{type: image}` / `{type: audio}` parts. **Not** `role: tool`.

**API:** `POST /videos/{id}/chat` `{ "message": "..." }` → `{ answer, citations, steps }`.

Save messages in **Postgres** (text + pointers to which times we showed). Do not store every JPEG in the DB.

**Tests:** FakeBrain returns canned JSON (`look` then `answer`). No GPU. Oversize `look` never runs a 2h ffmpeg.

---

## What we will not build here

- Native `tools=` / `tool_calls` as the product path
- Whisper / search
- Export, website, login
- Dumping the whole file into the prompt

---

## Locked (this correction)

| Topic | Decision |
|---|---|
| Loop owner | **Our state machine** |
| Model output | **vLLM structured output** — `response_format` JSON schema (`do`: look / listen / answer). This is Gemma 4 + vLLM’s native feature, not “ask nicely for JSON.” ([vLLM Gemma 4 recipe](https://docs.vllm.ai/projects/recipes/en/latest/Google/Gemma4.html)) |
| Native tool calling | **Not used** for this app’s brain |
| How it sees media | Image/audio **content parts**, not tool_response |
| Caps | Phase 2: 64 photos / 30s audio, reject oversize |
| Max rounds | **8** |
| Brain | **E4B** default (vLLM). 12B is an env switch if we want later. |
| Fake brain in tests | **Yes** (no GPU in CI) |

Also tell the model in the **prompt** what look/listen/answer mean. vLLM only forces the **shape**; the prompt teaches the **meaning**. ([vLLM note](https://docs.vllm.ai/projects/recipes/en/latest/Google/Gemma4.html))

---

## Plan (agent)

1. Pydantic schema for look / listen / answer
2. `app/agent/loop.py` — state machine
3. `app/agent/client.py` — vLLM OpenAI client, **`response_format: json_schema`**, no `tools=`
4. Attach Phase 2 bytes as multimodal parts
5. `POST /videos/{id}/chat`
6. Tests with FakeBrain

---

Implement only this file after Phases 1–2.

## Done when

- Chat API: “what happens at 0:10?” → JSON `look` → frames attached as images → JSON `answer`
- Oversize look refused by our machine, not by a host tool parser
- No `tools=` in the happy path
