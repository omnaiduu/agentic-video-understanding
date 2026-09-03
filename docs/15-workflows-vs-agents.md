# Workflows vs a free agent (small Gemma)

**Proposal, not yet locked.** Anthropic’s names, NVIDIA’s names, and whether we can drop 12B.

Short answer: **yes, this is a better v1 for us.** We already know the question types. Write those paths in **Python**. Use **Gemma 4 E4B** only for the small jobs it is good at (intent, extract a search phrase, read a slide, summarize, yes/no). Do **not** ask a 4B model to be a project manager with eight tools. That is what 12B was for — and we can delete that job.

Google’s product is still an **agent** (the model picks tools). We can still *look like* that to the user (timestamps, clips, follow-ups) while the **inside** is a workflow.

---

## Two names, one difference

[Anthropic — Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) (Dec 2024; they still use this split):

| | **Workflow** | **Agent** |
|---|---|---|
| Who decides the next step | **Your code** | **The model** |
| Path | Fixed (if this, then that) | Invented each time |
| Good when | You can list the jobs | You cannot predict the steps |
| Cost / chaos | Lower, repeatable | Higher, can wander |

They also name the building blocks we would use:

- **Routing** — classify the question, send it down one pipe
- **Prompt chaining** — step 1 output feeds step 2 (search → open frames → summarize)
- **Parallelization** — search transcript and pictures at the same time
- **Orchestrator–workers** — a model invents subtasks (we **do not** need this for v1)
- **Agent loop** — model + tools until it stops (Google; our old 12B plan)

NVIDIA **NeMo Agent Toolkit** calls the whole YAML a **workflow**. Inside it you pick a type:

- **`sequential_executor`** — steps in order (code path)
- **`router_agent`** — classify, then one specialist path
- **`react_agent` / `tool_calling_agent`** — the free agent

Their [AI-Q Blueprint](https://docs.nvidia.com/aiq-blueprint/latest/architecture/overview.html) is the same cartoon: **intent classifier first**, then a cheap path or a deep path.

We do **not** need to install NAT. Same idea in FastAPI functions. NAT YAML is optional later if we want NVIDIA-shaped config.

---

## Why 12B was in the old plan

E4B **has** vision and short audio. We picked 12B because it is **better at multi-step tool calling** (plan → search → zoom → search again). If **code** does the plan, that weakness goes away. 31B / 26B-A4B are the wrong family anyway (**no native audio**). We never needed “32B.”

E4B jobs that are in-distribution:

| Job | Example |
|---|---|
| **Intent** | talk / slide / visual / sound / count / export / follow-up / unknown |
| **Extract** | turn “when did she talk about the price” → search query `pricing` |
| **Classify** | “is there a bird in these 4 frames? yes/no + where” |
| **Read** | “what number is on this slide” (one or few frames) |
| **Summarize** | 3 transcript hits → one short answer with timestamps |

E4B should **not**: pick FPS, invent a third tool round, do arithmetic on 847 claps, or roam for 8 hops.

---

## Shape

```
user question
    │
    ▼
Gemma E4B: intent + search phrases   (one small JSON call)
    │
    ▼
Python: pick a named workflow
    │
    ├─ talk_qa        search_transcript → optional get_frames → summarize
    ├─ slide_qa       search_transcript and/or search_slides → get_frames → read
    ├─ visual_qa      search_visual → get_frames (zoom) → classify/describe
    ├─ sound_qa       search_audio → get_audio → classify/describe
    ├─ count_events   search_* → merge hits → len() in Python → spot-check 2 clips
    ├─ export_clip    last timestamps or search → ffmpeg (no LLM, or one confirm)
    ├─ follow_up      reuse session times → get_frames / get_audio
    └─ unknown        one bounded retry (parallel search) or “I can do talk/visual/sound/count/export”
```

Indexes, ffmpeg, caps, “rewatch not RAG-only” — **unchanged**. Only the **driver** changes: code, not a 12B ReAct loop.

### One walk-through: “What did she say about pricing? Give me the clip.”

1. E4B JSON: `intent=talk_qa`, `also_export=true`, `query="pricing"`.
2. Code: FTS on WhisperX words.
3. Code: if we want the slide, `get_frames` ~8s around the best hit, low FPS.
4. E4B: summarize those lines + optional frames → answer + timestamps.
5. Code: `export_clip` with duration cap.

No model ever chose a tool name.

---

## What we gain

- **Cheaper / faster** — E4B, fewer tokens, no 8-round wander.
- **Predictable** — same question shape → same path; easy to test.
- **Fits our own table** — [architecture](05-architecture.md) already listed question type → path. That *is* a workflow catalog.
- **Fits “count in Python”** — the model never owns the total.
- **Small model is enough** because we never asked it to be the agent.

## What we lose (honest) — and the fix

A **single** named recipe (`intent=talk_qa` only) does fail on combo questions, bad routing, and new wording.

**Fix (not 12B):** keep a **clipboard** in SQLite and let E4B tick a **verb menu** (several verbs per turn, max two plan rounds). Code glues “after the clap → slide → dog.” Details: [16-clipboard-and-verbs.md](16-clipboard-and-verbs.md).

This is **not** a clone of Gemini’s internals (their model still picks tools). The **user** still gets the same product: ask, timestamp, clip.

---

## Suggested default (if we lock this)

| Piece | Choice |
|---|---|
| Driver | **Clipboard + verb menu** ([16](16-clipboard-and-verbs.md)); named recipes are just common verb bundles |
| Brain | **Gemma 4 E4B** for intent / extract / read / summarize |
| 12B | Optional later, unknown/hard bucket only |
| 31B / “32B” | No — no audio, wrong job |
| Tools | Same eight; **code** calls them |
| NVIDIA shape | Optional NAT `router` + `sequential_executor` later; not required |

v1 is still: upload → indexes once → ask talk / look / listen / count / export. The change is **who holds the remote**: the script, not a big planner.
