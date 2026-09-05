# Phase 7 — Export a clip

**Status:** not locked. Human answers the questions at the bottom first.

Depends on: [Phase 1](phase-01.md) (file on disk + DELETE folder), [Phase 2](phase-02.md) (ffmpeg + reject oversize), [Phase 3](phase-03.md) (JSON loop). Indexes (4–6) are **not** required to cut; they only help find the times.

Product (short): after a time is known, **cut a short file the human can take away** and return a URL.

Related: [three jobs](../05-architecture.md) · [tools](../06-tools.md) · [phase map](../12-build-phases.md)

---

## Where we are

| Done on paper | This phase | Later |
|---|---|---|
| Hold file, scissors, Gemma JSON loop, three phone books | **Give the user a file** | Memory (8), website (9+) |

Find the time (indexes). Understand (look / listen). **This is the third job:** hand over a clip.

Still no website. The URL is an API path the later player/download button will use.

---

## What we are trying to do

You (or Gemma) already know start and end. We run ffmpeg, write a **small** mp4 or wav next to the original, and return a **link**. Fetching that link plays or downloads the cut.

This is **not** the Phase 2 scissors. Those cuts are **temp photos/wavs for Gemma**, then deleted. Export is a **kept file for the human**.

Question 2 does not re-cut unless someone asks again.

---

## What this is not

- **Not** finding a time. If start/end are unknown, search/look first (Phases 3–6).
- **Not** understanding. Export does not send media to Gemma.
- **Not** the whole original file. That is already `GET /videos/{id}/file`.
- **Not** S3/R2 yet. Local disk, same idea as Phase 1. Object storage later **behind the same functions**.
- **Not** a 10-minute dump. Same spirit as Phase 2: **cap, then reject**.
- **Not** the website download button (Phase 12). We only make the URL.

---

## Words

**Export** — write a clip or audio file to disk, give back a URL.

**`export_clip` / `export_audio`** — JSON actions beside look / listen / search_*. Our Python. Not vLLM tools.

**Cap** — max length we will cut. Oversize → error. Do not silent-shrink (same rule as Phase 2).

---

## How it will work

```
JSON: export_clip { start_s, end_s }
  → length check (must be ≤ cap)
  → ffmpeg write data/videos/{id}/exports/{export_id}.mp4
  → row in Export
  → next prompt / chat response includes url
```

Same for `export_audio` → `.wav`.

**HTTP**

- `GET /videos/{id}/exports/{export_id}` — stream the file (Range).
- `DELETE /videos/{id}` already deletes the **whole folder**, so exports go with the video.

Chat `answer` may include `export_url`. The loop can export, then answer with the link.

Audio-only file: `export_audio` works; `export_clip` errors (no picture track).

Invalid times (past duration, start ≥ end) → refuse. Oversize → refuse. Do not run ffmpeg on a 2h span.

---

## Options (what I would pick)

| Topic | My pick | Other options | Why my pick |
|---|---|---|---|
| Max length | **60 seconds**, reject oversize | 30s; 120s; silent-shrink | Older docs said 60s. Same reject rule as Phase 2. |
| Where files live | **Local disk** + `GET` URL | S3/R2/Modal Volume now | Phase 1 is local. Same folder. Swap storage later without changing JSON. |
| Auth on URLs | **None** | Signed URLs | No users yet. |
| JSON | **`export_clip`** and **`export_audio`** | One `export` with a kind field | Two jobs, two verbs. Matches [06](../06-tools.md). |
| Formats | Clip **mp4**; audio **wav** | m4a / mp3 for smaller audio | Wav matches Phase 2. Mp4 is what a player expects. |
| Cut style | **Re-encode** so start/end are exact | Stream-copy (`-c copy`) — fast, sloppy keyframes | 60s re-encode is cheap. A “give me that second” clip should start on time. |
| Direct HTTP create | **Python functions + JSON**. Tests call Python. Optional `POST` if the later UI wants it. | Must go through Gemma | Tests should not need the brain. |

**Libraries:** ffmpeg CLI (already Phase 2). No new ML. No new web framework.

---

## Plan (agent)

1. `Export` row: id, video_id, kind (clip/audio), start_s, end_s, path, created_at
2. Caps: duration ≤ 60s; valid range; audio-only cannot clip
3. `export_clip` / `export_audio` in `app/tools/`; ffmpeg writes under `exports/`
4. `GET /videos/{id}/exports/{export_id}` streams bytes
5. Add both actions to the vLLM JSON schema + prompt
6. Chat response can carry `export_url`
7. Tests: tiny fixture; 5s cut is playable; 10 min request never calls a 2h ffmpeg; DELETE video removes export files; FakeBrain `export_clip` then `answer`

Implement **only** this file after 1–6. No website. No session memory.

---

## Questions (lock these)

1. **Max 60 seconds. Oversize → reject** (do not silent-shrink). OK?
2. **Local disk + `GET` URL.** No auth. S3 later behind the same functions. OK?
3. **`export_clip` and `export_audio` in the same JSON form.** Chat can return the URL. OK?
4. **Formats: mp4 clip, wav audio.** Re-encode for exact times. OK?

When these are answered, mark **LOCKED**.

## Done when

- Tool returns a URL; fetching it is a short playable mp4/wav
- 10-minute request is rejected; original file unchanged
- Audio-only cannot `export_clip`
- Deleting the video deletes the exports
- Gemma is not sent the clip bytes (the **human** gets the URL)
