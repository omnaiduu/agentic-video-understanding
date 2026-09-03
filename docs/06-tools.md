# Tools

All tools are **functions the runtime may run**. Caps on window, FPS, export, frame budget. If we use the [clipboard driver](16-clipboard-and-verbs.md), **Python** calls them from a verb menu — Gemma does not pick raw tools.

## v1 (ship these)

| Tool | Input | Output | Helps the bot |
|---|---|---|---|
| `get_meta` | video id | duration, fps, has_audio | Plan; refuse 2h gulp |
| `search_transcript` | query string | `[{t, text, score}]` | Talk / “when did they say X” |
| `search_visual` | phrase | `[{t, score}]` | Silent look-like search (bird, red light) |
| `search_audio` | phrase | `[{t, score}]` | Chirp, clap, beep, gunshot |
| `get_frames` | start, end, fps | images to Gemma | **Eyes** — skim or zoom |
| `get_audio` | start, end | wav/slice to Gemma (keep ≤~30s) | **Ears** on a slice |
| `export_clip` | start, end | HTTPS URL to mp4 | User leaves with video |
| `export_audio` | start, end | HTTPS URL | User leaves with sound |

### `get_frames` policy (server clamps)

- Skim: long span, **low** FPS (e.g. ≤0.25) or few frames
- Zoom: **≤ ~8s**, FPS up to ~8–10
- Never `get_frames(0, 7200, fps=1)` — rewrite or error

## Later (low hanging / if needed)

| Tool | When |
|---|---|
| `crop_frame` | Tiny object in a frame already fetched (mini Agentic Vision) |
| `search_slides` | On-screen text nobody spoke — ColQwen on **unique** slides; see [14-slides-and-on-screen-text.md](14-slides-and-on-screen-text.md) |
| `ocr_frame` | Dense slide text Gemma misreads — **one frame**, not ingest |
| `count_events` | Thin wrapper: search + merge + `len()` so the model doesn’t arithmetic-hallucinate |

## Not tools in this product (v1)

- `search_notes` — no caption diary
- Arbitrary Python / full Agentic Vision sandbox
- Web search, shell, calendar

## Agentic Vision vs these tools

**Agentic Vision (Google, still images):** crop/zoom/annotate **one photo** via code, feed the crop back.

**Agentic video (Google + us):** jump **in time**, change FPS.

`crop_frame` is Vision. `get_frames(t0,t1,fps)` is Video. We need video first; crop is optional polish.

## Example: “Find the flying bird and give me the clip”

1. `search_visual("bird flying")` → 1:04
2. `get_frames(1:03, 1:06, fps=8)` → Gemma confirms
3. `export_clip(1:03, 1:06)` → URL
4. Text answer + timestamp + link
