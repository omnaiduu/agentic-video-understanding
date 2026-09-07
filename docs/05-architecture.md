# Architecture

## Picture

```
                    INGEST (once per video)
  video.mp4 ──► disk  data/videos/{id}/
           ──► ffmpeg 1 FPS ──► SigLIP 2 ──► VisualFrame (pgvector)
           ──► audio ──► Whisper turbo ──► TranscriptLine (tsvector + E5)
                    └──► 3s / 1.5s hop ──► CLAP ──► AudioChunk (pgvector)


                    QUESTION (many times)
  user ──► FastAPI ──► our state machine
                      │
                      ├─ Gemma E4B fills JSON (vLLM json_schema)
                      ├─ we run look / listen / search_* / export_*
                      ├─ photos/wav attached as normal content parts
                      └─► answer + timestamps + optional export_url
```

On-the-fly = the **loop**. Cache = **don’t rebuild** Whisper/SigLIP/CLAP.

## Three jobs (do not mix)

| Job | Who |
|---|---|
| **Find** the time | Indexes + `search` / `search_visual` / `search_audio` |
| **Understand** | Gemma on `look` / `listen` (Phase 2 scissors) |
| **Give the user a file** | `export_*` (kept file + GET URL) |

## Question types → path

| Type | Example | Path |
|---|---|---|
| Talk | “What did she say about pricing?” | `search` → maybe `look` to confirm slide |
| Slide text | “What number was on the slide then?” | Transcript (or visual) for time → `look` → Gemma reads |
| Silent visual | “Red light / flying bird” | `search_visual` → `look` |
| Sound | “When did the bird chirp?” | `search_audio` → `listen` |
| Count events | “How many claps?” | `search_audio` → merge hits → **count in code** → spot-check |
| Fast action | “How many shots in 10s?” | Find window → `look` (still ≤ 64 photos) |
| Follow-up | “Was a car in that frame?” | Session last 3 times as **text**; no re-ingest |
| Export | “Give me that clip” | `export_clip` after times are known |

## Loop rules

1. Pointer first: duration, ids — do not load the movie into Gemma.
2. Search before gulp.
3. Rewatch is capped: **64 photos or 30s of sound**. Oversize → reject, tell the model to try smaller.
4. Max **8** JSON rounds.
5. Multi-turn: `session_id` + last 3 windows as text (Google’s `step_list` idea). Do not re-attach old JPEGs.

## Why this matches Google

Google: tools on the raw file, transcript-first, adaptive FPS, pay for slices.  
We: same idea; **Act is our Python**. We **add** SigLIP + CLAP so long silent/sound queries are not a Gemma marathon.

## Counting (no architecture fork)

Do **not** ask Gemma to watch 2 hours and keep a running total.

```
search_audio → candidate times → merge nearby → count in Python
→ Gemma listen/look on 2–3 samples if we need to verify
```

Stadium applause may be one blob, not N claps. Product should say “applause 1:00–1:40” when that’s the truth.
