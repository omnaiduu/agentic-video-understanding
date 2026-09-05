# Phase 3 — Brain loop

**Status:** not locked. Human answers the questions at the bottom first.

Depends on: [Phase 1](phase-01.md) (a file) and [Phase 2](phase-02.md) (scissors). Do not re-open those.

Product (short): you **ask a question**. The model may **cut a small piece**, look or listen, then **answer**. Still no Whisper, no picture search, no website.

Related: [architecture](../05-architecture.md) · [Gemma](../07-models-and-indexes.md) · [phase map](../12-build-phases.md)

---

## What we are trying to do

This is the **loop** the whole product is built around:

1. You ask something about a stored video (or audio).
2. The model thinks: “I need to look at 0:10.”
3. **Our server** runs the Phase 2 cutter (caps still apply).
4. We give the model those photos or that sound.
5. It answers, or it asks to look at another short piece.
6. Stop after a few rounds. Return the text answer + times it looked at.

Without search indexes, this only works well if **the question already has a time** (“what happens at 0:10?”). “Find the red light in two hours” waits for later phases.

There is still **no website**. You hit an API (`POST /videos/{id}/chat`).

---

## Words

**Brain** — Gemma 4. It can read text, see photos, hear short audio. It cannot watch a 2-hour file.

**Loop** — model asks for a cut → we cut → we show it the cut → repeat → answer.

**Tool call** — the model outputs “run `get_frames` with these times.” Our code runs it. This is what Gemma 4’s docs show.

**Structured output** — we force the model to fill a JSON shape (`{"action": "get_frames", "start": 10, ...}`). Same idea, we parse JSON instead of a native tool call. Extra glue. Worse when it needs **several** cuts in a row.

**Round** — one “ask for a cut → get the cut back.” We cap how many rounds so it cannot loop forever.

---

## How it will work

```
you → POST /videos/{id}/chat  { "message": "What happens at 0:10?" }

server:
  tell Gemma: here is duration, here are tools get_meta / get_frames / get_audio
  while rounds < 8:
    if Gemma wants a tool:
      run Phase 2 function (caps!)
      send back: short text + the actual photos or wav
    else:
      return her answer
```

**Photos/audio to Gemma:** after ffmpeg, we attach **real image/audio parts** on the next turn. We do not stuff JPEGs into a JSON string. (Gemma’s official tool *result* format is text; our runtime adds the media. Same as we said in Phase 2.)

**What you get back:** `{ answer, citations: [{t}], tool_trace }`  
`tool_trace` = which tools ran (for debugging). Citations = times it looked at.

Save the user and assistant messages in SQLite so Phase 8 is not a rewrite.

---

## What we will not build here

- Whisper / SigLIP / CLAP / search tools
- Export clip URL
- Website
- Login
- Dumping the whole video into the prompt

---

## I would pick

| Topic | Pick | Why |
|---|---|---|
| How Gemma asks for a cut | **Native tool calling** | Gemma 4 supports it. Fits a multi-step loop. Structured JSON is a fallback if a host is bad at tools. |
| Model | **Gemma 4 12B Unified** default | Sees + hears + tools. E4B is a cheaper env switch, not a second app. |
| Where it runs | **`MODEL_BASE_URL` + `MODEL_NAME`** | Same code for Ollama, vLLM, or Modal. |
| Tests | **Fake brain** (scripted: “must call get_frames for 0:10”) | CI needs no GPU. |
| Max rounds | **8** | Stop infinite loops. |
| Caps | Unchanged from Phase 2 | 64 photos / 30s audio, reject oversize. |

---

## Plan (agent)

1. `app/agent/client.py` — OpenAI-compatible or Transformers chat; send tools + multimodal parts
2. `app/agent/loop.py` — run tools, attach frames/audio, cap rounds
3. `POST /videos/{id}/chat`
4. `ChatMessage` table (video_id, role, content, created_at)
5. Tests with FakeBrain: time question → `get_frames` with a small window → answer; oversize tool never reaches ffmpeg
6. README: how to point `MODEL_BASE_URL` at a real Gemma

No React. No Whisper.

---

## Questions (answer these to lock)

1. **How the model asks for a cut:** native **tool calling** (recommended), or **structured JSON**, or you don’t care (we pick tool calling)?
2. **Tests without a GPU:** fake brain in CI, real Gemma only when `MODEL_BASE_URL` is set. OK?
3. **Default model 12B**, cheaper E4B via env. OK?

When these are answered, mark **LOCKED** and implement only this file.

## Done when

- `POST /videos/{id}/chat` with “what happens at 0:10?” returns an answer
- Scripted test proves `get_frames` ran on a **short** window
- A too-big tool request is rejected
- No search, no UI
