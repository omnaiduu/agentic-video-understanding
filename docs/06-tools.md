# Tools

These are **Python functions our state machine runs**. Gemma does not call OpenAI-style tools. It only emits JSON (`do`: look, listen, search, …). Caps are enforced in Python.

## v1 (ship these)

| JSON `do` | Python | Output | Helps |
|---|---|---|---|
| *(meta, not a chat verb)* | `get_meta` | duration, fps, has_audio | Plan; refuse 2h gulp |
| `look` | `get_frames` | JPEGs + times to Gemma as **image parts** | **Eyes** |
| `listen` | `get_audio` | wav to Gemma as **audio part** (≤30s) | **Ears** |
| `search` | `search_transcript` | top ~8 `{t, text}` as **text** | Talk / “when did they say X” |
| `search_visual` | `search_visual` | top ~8 `{t, score}` as **text** | Silent look-like search |
| `search_audio` | `search_audio` | hits + merged count as **text** | Chirp, clap, beep |
| `export_clip` | `export_clip` | GET URL to mp4 (≤60s) | User leaves with video |
| `export_audio` | `export_audio` | GET URL to wav | User leaves with sound |
| `answer` | *(stop)* | text + times | Done |

### `look` / `listen` policy (server clamps)

- One rule: **64 photos or 30 seconds of sound**. Count before cut. Oversize → **reject** (do not silent-shrink).
- Never extract 0–7200s at 1 FPS.
- Temp JPEGs/wavs for Gemma are deleted after the round. Export files are **kept**.

## Later (low hanging / if needed)

| Tool | When |
|---|---|
| `crop_frame` | Tiny object in a frame already fetched (mini Agentic Vision) |
| `ocr_frame` | Dense slide text Gemma misreads — **one frame**, not ingest |

Counting is already inside `search_audio` (merge + `len()`). No extra verb required.

## Not tools in this product (v1)

- `search_notes` — no caption diary
- Native `tools=` / `tool_calls`
- Arbitrary Python / full Agentic Vision sandbox
- Web search, shell, calendar
- ColQwen `search_slides`

## Agentic Vision vs these tools

**Agentic Vision (Google, still images):** crop/zoom/annotate **one photo** via code, feed the crop back.

**Agentic video (Google + us):** jump **in time**. `look` is Video. `crop_frame` is Vision. We need video first; crop is optional polish.

## Example: “Find the flying bird and give me the clip”

1. JSON `search_visual` “bird flying” → 1:04
2. JSON `look` 1:03–1:06 → Gemma confirms
3. JSON `export_clip` → URL
4. JSON `answer` + timestamp + link
