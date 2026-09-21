# E4B thinking on/off

The [12B A/B is closed](e4b-vs-12b-plan.md). Default brain stays **Gemma 4 E4B**. This note is the thinking experiment: same leftover questions, crutches still off.

Thinking will not pin 11.00s and is not a clap detector. The question was whether the **planner** starts listening before it exports (H7) and whether it still guesses claps (H5).

Related: [why 4B is enough](why-4b-is-enough.md) · [hidden-intent questions](live-intent-questions.md)

**Verdict:** thinking **stays off** as default. The suite H7 did listen-then-export (the 12B path). A smoke of the same question still skipped listen. Clap counting got worse. Keep the Watch checkbox; do not pay the second GPU for every chat.

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
# gitignored .env:
# VLLM_THINKING_BASE_URL=https://<workspace>--agentic-video-brain-e4b-thinking-server.<region>.modal.direct/v1
```

Sources: [Gemma thinking](https://ai.google.dev/gemma/docs/capabilities/thinking) · [vLLM Gemma 4 recipe](https://docs.vllm.ai/projects/recipes/en/latest/Google/Gemma4.html) · [vLLM reasoning outputs](https://docs.vllm.ai/en/stable/features/reasoning_outputs/) · [vLLM #50938](https://github.com/vllm-project/vllm/issues/50938)

---

## Live scoreboard

Same tape `c1d9beb7-5465-4f47-9d53-2d6b299104b5`, indexes `ready`, crutches **off**. Fresh session per question. All eight HTTP **200** on both paths. JSON stayed BrainAction (no `---` preamble).

Traces: `backend/eval/results/hidden-intent-e4b-off.json` (this run) and `hidden-intent-e4b-thinking.json`.

| Q | Thinking off (this run) | Thinking on (this run) |
|---|---|---|
| **E1** Pro cost | **pass.** Speech → $99. | **pass.** Speech → $99. |
| **H1** $99 on red? | **pass** (scorer). Still likes to lead with Yes. | **partial.** Looked at RED ALERT, then Q3. “Could not confirm… red emergency screen only displays RED ALERT.” Clearer on the trap; scorer wanted a sharper “not on red.” |
| **M3** ship this quarter | **pass.** Slides + look at Q3. | **pass.** Same. |
| **M4** tone + screen | **pass.** Sound 9–12 → listen+look 9–12. Named RED ALERT **and** Q3. | **partial.** Sound 9–12 → listen+look 9–12. Named **only RED ALERT** (window start). Same 12B miss. |
| **M1** printed color vs speech | **fail.** Slides + looks; no `search` speech. | **partial.** Opened both books (look + speech). Named yellow $99; no “match” sentence. |
| **H5** claps | **partial.** Listened 6–9. Pointed at hit ranges; did not say zero. | **partial** (worse). Listened four windows and **heard claps** that are not there. Thoughts say “found 1 clap” in 6–9s (silence/red). Not a numeric five, still a false hear. |
| **H7** clip the beep | **fail.** Sound 9–12 → **look 10.5–13.5 → export 10.5–13.5, no listen.** | **pass.** Sound 9–12 → **listen 9–12 → export 9–12.** Flags: `listened_before_export`, `exported_heard_range`. Cut is still the mixed 9–12 window (red then Q3), but it **heard** that window first. |
| **H8** walk | **pass.** Skip-ahead. Names Pricing, RED ALERT, Q3. | **pass.** Same names. |

Automated tallies: off **5 pass / 1 partial / 2 fail**. On **4 pass / 4 partial / 0 fail**.

### Smoke (beep clip, thinking on, before the suite)

HTTP 200, three thoughts, parseable JSON. Path was **search_audio 9–12 → look 9–12 → export 9–12** (no listen). So thinking does **not** always pick listen. The suite run did.

Quoted thoughts from that smoke:

- search_audio: “Search for beep… then `export_clip` around that time.”
- look: “I should pick one to **listen**… I’ll pick [9.0s–12.0s]… The user wants a 3-second clip. I can use this range. First, `look`… then export 9–12.” It named listen, then skipped it.
- export_clip: frames showed RED ALERT; still exported 9–12.

### Suite H7 thoughts (the pass)

- search_audio: find beep, then clip.
- listen: “I should start by **listening** to [9.0s–12.0s], to confirm the beep.”
- export_clip: “I listened to [9.0s–12.0s]. The audio contains the beep. Export 9–12.”

That is the planner 12B used. It still exported the **whole similar-audio window**, not a tight tone cut. Thinking is not a beep detector.

### Why default stays off

- H7 is **not reliable**. Suite listened; smoke looked and dumped 9–12.
- H5 **hallucinated claps** after extra listens (the 12B failure mode).
- M4 described the window start (RED ALERT), not the tone.
- A second L4 is real cost. Off-path json_schema on the original worker stayed intact (thinking-off E1 still $99).

Use the Watch checkbox when you want to *see why* a move happened, or to try listen-then-cut. Do not switch `GEMMA_THINKING` on in `.env`.

Next experiment: [System One picker](system-one-picker.md) — skip JSON decode on the first search-routing hop only. Default off.
