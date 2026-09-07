# Phase 8 — Remember last times

**Status: LOCKED** (last 3 windows; `session_id`; text pointers; no auto-delete).

Depends on: [Phase 3](phase-03.md) (`POST /videos/{id}/chat`, messages in Postgres). Indexes and export already exist; this phase only **reuses times**.

Product (short): a follow-up like “was a car in **that** frame?” uses the **same video** and the **last times**, without re-ingest and without searching the whole tape again.

Related: [loop rules](../05-architecture.md) · [Google `step_list`](../10-references.md) · [phase map](../12-build-phases.md)

---

## What we are trying to do

Turn 1 finds a moment. Turn 2 (“that frame”) uses **session last_times** as **text** in the prompt. Gemma may `look` / `listen` again. Whisper / SigLIP / CLAP do **not** run again. Old JPEGs/wavs are **not** re-attached.

Same idea as Google’s `step_list`. Memory is **our** state. No new JSON verb.

This is the last slice of the **first** backend pass (hold → scissors → loop → three books → export → memory). **Phase 13** adds the slide book after the website exists. Same app.

---

## Locked

**Why text pointers, not old photos:** replaying frames would blow the 64-photo / 30s caps. Gemma can `look` again if she needs eyes.

**Why not auto-delete the video:** the later library lists videos. Wiping on “bye” would empty it. **`DELETE /videos/{id}`** still removes row + folder + sessions.

---

## Words

**Session** — one chat thread on one video.  
**`last_times`** — last 3 `{start_s, end_s, kind}` from look / listen / search / export.  
**`session_id`** — sent on the next chat POST. Omit → new thread.

---

## How it will work

```
POST /videos/{id}/chat  { "message": "...", "session_id": optional }

  no id → create Session
  yes   → load for this video (404 if wrong)

  prompt: recent text + last_times as text
  loop as Phases 3–7
  push new windows; keep last 3
```

Prompt: “that / there / the clip / that frame” → use last_times first.

---

## Locked details

| Topic | Decision |
|---|---|
| Windows | **Last 3** |
| Prompt | Text messages + last_times as **text**. No old image/audio parts |
| Session | Optional `session_id`; omit → new. Response includes it |
| Store | Postgres `Session` + `ChatMessage` (pointers, not blobs) |
| JSON verb | **None** |
| Files | Session end does **not** delete the video |
| Delete video | Row + folder + sessions |
| Not this phase | Redis, `crop_frame`, `ocr_frame`, website |

---

## Plan (agent)

1. `Session` + `ChatMessage` tables
2. Chat accepts optional `session_id`
3. Inject last_times; do not replay old media
4. Keep last 3 windows after look / listen / search / export
5. Tests with FakeBrain: two-turn “that frame”; wrong id → 404; DELETE video removes sessions

Implement only this file after 1–7.

## Done when

- Two-turn test does not re-ingest and does not search from scratch if times exist
- Old frames/audio are not re-attached every turn
- New session starts clean; wrong id fails clearly
