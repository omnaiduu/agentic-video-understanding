# Architecture

## Picture

```
                    INGEST (once per video)
  video.mp4 ──► ffmpeg 1 FPS ──► SigLIP 2 ──► visual vectors + times
           ──► audio ──► Whisper ──► transcript.json (FTS)
                    └──► 1–5s chunks ──► CLAP/GLAP ──► audio vectors + times
           ──► store file in object storage


                    QUESTION (many times)
  user ──► API ──► Gemma 4 12B (or E4B)
                      │
                      ├─ search_transcript / search_visual / search_audio
                      ├─ get_frames / get_audio     (short slices into Gemma)
                      └─ export_clip / export_audio (ffmpeg → storage URL)
                      │
                      └─► answer + timestamps + optional link
```

On-the-fly = the **loop**. Cache = **don’t rebuild** Whisper/SigLIP/CLAP.

The picture above is the **agent** driver (12B picks tools). A cheaper driver is a **workflow**: E4B classifies intent, **Python** runs the row in the table below. Same tools. See [15-workflows-vs-agents.md](15-workflows-vs-agents.md).

## Three jobs (do not mix)

| Job | Who |
|---|---|
| **Find** the time | Indexes + `search_*` |
| **Understand** | Gemma on `get_frames` / `get_audio` |
| **Give the user a file** | `export_*` |

## Question types → path

| Type | Example | Path |
|---|---|---|
| Talk | “What did she say about pricing?” | `search_transcript` → maybe `get_frames` to confirm slide |
| Slide text | “What number was on the slide then?” | Transcript (or visual) for time → `get_frames` → Gemma reads |
| Silent visual | “Red light / flying bird” | `search_visual` → `get_frames` zoom |
| Sound | “When did the bird chirp?” | `search_audio` → `get_audio` confirm |
| Count events | “How many claps?” | `search_audio` → merge hits → **count in code** → spot-check |
| Fast action | “How many shots in 10s?” | Find window → `get_frames` high FPS → Gemma or code |
| Follow-up | “Was a car in that frame?” | Session remembers last times; no re-ingest |
| Export | “Give me that clip” | `export_clip` after times are known |

## Loop rules

1. Pointer first: duration, ids — do not load the movie into Gemma.
2. Search before gulp.
3. Rewatch a **short** window (e.g. ≤8s zoom, skim at very low FPS only if search is empty).
4. Cap frames per question (e.g. 32–64).
5. Cap tool rounds (e.g. 8) — or **2 plan JSON rounds** if we use the [clipboard driver](16-clipboard-and-verbs.md)
6. Multi-turn: keep `handle_id` + last timestamps (Google’s `step_list` idea) — the **clipboard**

## Why this matches Google

Google: tools on the raw file, transcript-first, adaptive FPS, pay for slices.  
We: same tools; we **add** SigLIP + CLAP so long silent/sound queries are not a Gemma marathon. Google may do similar internally; they didn’t publish CLIP/CLAP.

## Counting (no architecture fork)

Do **not** ask Gemma to watch 2 hours and keep a running total.

```
search_* → candidate times → merge nearby → count in Python
→ Gemma get_audio/get_frames on 2–3 samples if we need to verify
```

Stadium applause may be one blob, not N claps. Product should say “applause 1:00–1:40” when that’s the truth.
