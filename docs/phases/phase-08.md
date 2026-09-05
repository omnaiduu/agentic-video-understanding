# Phase 8 — Remember last times

**Status:** not locked. Human answers the questions at the bottom first.

Depends on: [Phase 3](phase-03.md) (`POST /videos/{id}/chat`, messages in Postgres). Indexes and export already exist; this phase only **reuses times**.

Product (short): a follow-up like “was a car in **that** frame?” uses the **same video** and the **last times**, without re-ingest and without searching the whole tape again.

Related: [loop rules](../05-architecture.md) · [Google `step_list`](../10-references.md) · [phase map](../12-build-phases.md)

---

## Where we are

| Done on paper | This phase | Later |
|---|---|---|
| File, scissors, JSON loop, three phone books, export URL | **Follow-ups** | Website (9–12) |

This is the **last backend** slice. After this, the API can do the full human loop except a pretty UI.

---

## What we are trying to do

Turn 1: “where is the red light?” → search → look 1:04 → answer.

Turn 2: “was a car in that frame?”

**Wrong:** run SigLIP on two hours again, or send every old JPEG.

**Right:** we already have times on the **session**. We put those times in the next prompt as **text**. Gemma may `look` at 1:03–1:06 and `answer`. Indexes stay untouched.

Same idea as Google’s `step_list`: keep a handle on the file plus the last steps’ timestamps.

---

## What this is not

- **Not** re-ingest. Whisper / SigLIP / CLAP already ran once.
- **Not** a new phone book.
- **Not** Redis, not a second database.
- **Not** `crop_frame` / `ocr_frame` ([06](../06-tools.md) later list).
- **Not** the website. `session_id` is a string the later UI will keep.
- **Not** dumping old photos and wavs into every follow-up (that would blow the 64-photo / 30s caps).

---

## Words

**Session** — one chat thread on **one** video. Has an id.

**`last_times`** — a short list of `{start_s, end_s, kind}` from recent look / listen / search / export.

**`session_id`** — you send it on the next `POST /videos/{id}/chat`. Miss it → new thread.

---

## How it will work

```
POST /videos/{id}/chat  { "message": "...", "session_id": "..." optional }

  no session_id → create Session, return its id
  yes           → load Session for this video (404 if wrong video)

  prompt includes:
    - recent **text** messages (not old image/audio parts)
    - last_times as text: "last windows: look 1:03–1:06, …"

  loop as Phase 3–7 (look / listen / search_* / export / answer)

  after each successful action: append to last_times (keep last N)
  save ChatMessage text + pointers, not JPEGs
```

Prompt tells the model: if the user says “that / there / the clip / that frame”, **use last_times first**. Do not search the whole tape unless those times are missing or the question is clearly about a new moment.

**DELETE /videos/{id}** still deletes the folder **and** that video’s sessions/messages.

---

## Options (what I would pick)

| Topic | My pick | Other options | Why my pick |
|---|---|---|---|
| How many windows | **Last 3** | Last 1 (too brittle); entire history (noisy) | Enough for “that” and “the one before”. |
| What we store | **Text messages + last_times pointers** | Re-send old photos every turn | Caps. Gemma can `look` again if she needs eyes. |
| Session | **`session_id` on chat**; omit → new | One global thread per video | UI can have one thread; tests can start clean. |
| Store | **Postgres** Session + ChatMessage | Redis | We already have Postgres. Demo does not need a cache box. |
| New JSON verb | **None** | `use_last` action | Memory is **our** state. The prompt already has the times. |
| Files when chat ends | **Do not auto-delete the video** | Close session → wipe files (Phase 1 intent) | The later library lists videos. Wiping on “stop talking” would empty it. **`DELETE /videos/{id}`** still removes row + folder + sessions. |

**Libraries:** SQLModel / Postgres already there. No Redis. No new ML.

---

## Plan (agent)

1. `Session`: id, video_id, last_times JSON, created_at, updated_at
2. `ChatMessage`: session_id, role, text, times pointers (no blobs)
3. `POST /videos/{id}/chat` accepts optional `session_id`; response includes it
4. Inject last_times + recent text into the prompt; **do not** replay old image/audio parts
5. After look / listen / search / export, push onto last_times; keep last 3
6. Tests with FakeBrain, **no GPU**:
   - Turn 1 look at 10s → answer
   - Turn 2 “was a car in that frame?” → model is shown last_times around 10s; **no** ingest; **no** full-tape search in the test double
   - Wrong `session_id` / other video → 404
   - DELETE video removes sessions

Implement **only** this file after 1–7. No React.

---

## Questions (lock these)

1. **Keep the last 3 time windows** on the session. OK?
2. **`session_id` on chat**; omit → new session. Same video. OK?
3. Follow-up prompt gets last times as **text**, not old photos/wavs. Gemma may `look` / `listen` again. OK?
4. **Do not auto-delete the video when a session ends.** `DELETE /videos/{id}` still wipes files + sessions. OK? (You had said demo files shouldn’t live forever — this keeps an explicit delete instead of wiping on “bye”.)

When these are answered, mark **LOCKED**. Backend phases are then complete; next is the website.

## Done when

- Two-turn test: find a moment, then “that” moment does not re-ingest and does not search from scratch if times exist
- Old frames/audio are not re-attached every turn
- New session starts clean; wrong id fails clearly
- No Redis; no crop/OCR
