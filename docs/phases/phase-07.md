# Phase 7 — Export a clip

**Status: LOCKED** (60s cap, reject oversize; local disk + GET URL; mp4 / wav; re-encode).

Depends on: [Phase 1](phase-01.md) (file on disk + DELETE folder), [Phase 2](phase-02.md) (ffmpeg + reject oversize), [Phase 3](phase-03.md) (JSON loop). Indexes (4–6) only help **find** the times.

Product (short): after a time is known, **cut a short file the human can take away** and return a URL.

Related: [three jobs](../05-architecture.md) · [tools](../06-tools.md) · [phase map](../12-build-phases.md)

---

## What we are trying to do

Start and end are known. ffmpeg writes a **small** mp4 or wav under the video folder. We return a **link**. Fetching it plays or downloads the cut.

This is **not** Phase 2 scissors (temp media for Gemma, then deleted). Export is a **kept file for the human**. Gemma does not get the clip bytes.

---

## Locked

**Why reject, not shrink:** same rule as look/listen. A 10-minute ask must not silently become 60s or run ffmpeg on the whole tape.

**Why local disk:** Phase 1 is local. S3/R2 later behind the same `export_*` functions and the same GET path.

---

## Words

**Export** — write a clip or audio file, give back a URL.  
**Cap** — max 60s. Oversize → error.  
**`export_clip` / `export_audio`** — JSON actions. Our Python. Not vLLM tools.

---

## How it will work

```
JSON: export_clip { start_s, end_s }
  → length ≤ 60s
  → ffmpeg re-encode → data/videos/{id}/exports/{export_id}.mp4
  → Export row
  → chat may include export_url
```

`export_audio` → `.wav`.

`GET /videos/{id}/exports/{export_id}` streams the file (Range).  
`DELETE /videos/{id}` deletes the folder, so exports go with the video.

Audio-only: `export_audio` works; `export_clip` errors.

---

## Locked details

| Topic | Decision |
|---|---|
| Max length | **60s**. Oversize → **reject**. Do not silent-shrink |
| Store | Local disk under `exports/` |
| HTTP | `GET /videos/{id}/exports/{export_id}` — no auth |
| Later | Object storage behind the same functions |
| JSON | `export_clip` and `export_audio` in the vLLM schema |
| Formats | Clip **mp4**; audio **wav** |
| Cut | **Re-encode** (exact start/end, not keyframe copy) |
| Chat | Response may include `export_url` |
| Tests | Call Python / FakeBrain; no GPU |

---

## Plan (agent)

1. `Export` row: id, video_id, kind, start_s, end_s, path
2. Caps: ≤ 60s; valid range; audio-only cannot clip
3. `export_clip` / `export_audio` in `app/tools/`
4. GET stream; DELETE video removes files
5. Wire both actions into the Phase 3 loop
6. Tests: 5s playable; 10 min never calls 2h ffmpeg; FakeBrain export then answer

**Libraries:** ffmpeg CLI. No new ML.

Implement only this file after 1–6.

## Done when

- URL fetches a short playable mp4/wav
- 10-minute request is rejected; original unchanged
- Audio-only cannot `export_clip`
- Deleting the video deletes the exports
- The human gets the URL; Gemma does not get the clip bytes
