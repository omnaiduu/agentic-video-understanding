# Live query retest

16s clip: **0–6s Pricing / Pro $99** · **6–10s RED ALERT** · **10–16s Q3 + beep**  
PR: https://github.com/omnaiduu/agentic-video-understanding/pull/25  
Video: `af12a3ad-c22d-4359-8de9-ec7baff9eb6a`

**14/14 passed.** Two failed on the first pass, then passed after a fix.

## Look at the start

- **Should:** Look 0–2s and read the heading and price.
- **Did:** Look 0–2s. “Pricing” / “Pro $99 per month.”
- **Proved:** Look works; it reads the real slide, not a guess.

## Look 0–4s (default fps)

- **Should:** Look without blowing Gemma’s 8k context (no 500).
- **Did:** HTTP 200, four 512px frames, answered Pricing / Pro $99.
- **Proved:** Smaller/slower look JPEGs fit 8k.

## Listen

- **Should:** Listen 0–6s and report what was said.
- **Did:** “Pro plan is $99 a month.”
- **Proved:** Listen hears the spoken price.

## Search speech

- **Should:** Search the transcript for pricing.
- **Did:** `search` hits at 0.00s and 3.12s; same price in the answer.
- **Proved:** Whisper search finds the line.

## Search pictures

- **Should:** Find the red alert screen.
- **Did:** `search_visual` at 6s, then look. “RED ALERT” in white on red.
- **Proved:** SigLIP hit + look matches the red beat.

## Search sound

- **Should:** Find the beep near the end; never 422.
- **Did first:** **422** in a long session (invalid JSON after a listen).
- **Did after fix:** HTTP 200, listen 13.5–16s, “I heard a beep.”
- **Proved:** Audio search works; 422 stitch works.

## Search slides — “Which slide had Pro $99?”

- **Should:** Rank the **0–6s Pricing** slide first, look, answer from pixels. Do not paste $99 onto the red frame.
- **Did first:** Ranked **6s red first**. Looked and said it was RED ALERT, **not** Pro $99. Ranking was dummy tokens (`SLIDE_EMBEDDER=fake` in the shell).
- **Did after ColQwen:** Hits **0.00, 10.00, 6.00**. Looked at 0s. “Pro $99 per month.” Same in the UI Details.
- **Proved:** Real ColQwen ranks Pricing first; after look it trusts pixels.

## Export

- **Should:** Cut a 4s clip of the pricing slide from 0s.
- **Did:** Returned an export URL.
- **Proved:** Export is wired.

## Follow-up

- **Should:** Reuse the last clip/times, not search the whole tape again.
- **Did:** Answered from the last 0–4s clip: Pricing / Pro $99.
- **Proved:** Memory of last windows works.

## Slides still building

- **Should:** If the slide book isn’t ready, look, then answer — don’t only apologize.
- **Did:** `search_slides` not ready → look 0–1s → “Pro $99” under Pricing.
- **Proved:** Look-then-answer fallback.

## Stuck ingest

- **Should:** A book left `processing` > 70 min becomes `error` on GET.
- **Did:** Zombie `2343e2a0-cff1-4cfd-9758-875eb047dce0` speech `processing` → **error**.
- **Proved:** Stale ingest doesn’t sit on “building” forever.

## Chat while indexes build

- **Should:** Chat on once the file is playable; show that books are still building.
- **Did:** Input enabled; hint “Indexes are still building…”; look still answered Pricing.
- **Proved:** Chat isn’t locked on index status.

Direct ColQwen: “Pro $99” scores **9.78 at 0s** vs **6.90 on red**.

## How each query runs

Gemma never calls tools. The website posts `{ message }` to `POST /videos/{id}/chat`. FastAPI loads the file path, index statuses, last 3 time windows, and the last Q&A. It asks Gemma (Modal vLLM) for one JSON object: `{ do, start_s, end_s, fps, query, answer, times }`. The **laptop** then does the move. The result comes back as a normal user message (not a tool result). Repeat until `do: answer` (max 8 moves).

Ingest already wrote the books (Whisper / SigLIP / CLAP / ColQwen) into Postgres. Search only reads those rows. Look and listen always cut **now** with ffmpeg.

| You ask | Gemma usually fills | Laptop does | Gemma sees next | Then |
|---|---|---|---|---|
| Look at 0–2s / 0–4s | `look` + window | ffmpeg JPEGs, max width 512, default 1 fps | The actual photos | `answer` from pixels |
| Listen 0–6s | `listen` + window | ffmpeg 16 kHz mono wav (≤30s) | The audio clip | `answer` from sound |
| What do they say about pricing? | `search` + query | Hybrid FTS + E5 vectors on `transcript_lines`, top 8 `{t, text}` | Hit list as text, not the whole talk | Often `answer` from those lines |
| Find the red alert | `search_visual` + query | SigLIP vector KNN on `visual_frames`, top 8 times | Scores + times only | `look` at a hit, then `answer` |
| Find the beep | `search_audio` + query | CLAP KNN on `audio_chunks`, merge nearby hits | Windows + count | `listen` at a hit, then `answer` |
| Which slide had Pro $99? | `search_slides` + query | Modal ColQwen embed of the phrase; MaxSim vs unique slide patches | `{t, score}` list | `look` at top hit (~1s), then `answer` from that JPEG |
| Export a 4s clip | `export_clip` + window | ffmpeg mp4 onto disk (≤60s) | A GET URL, not the bytes | `answer` including the URL |
| What was on that clip? | often `answer` (or look/listen at last times) | Nothing new if memory is enough | Last 3 windows as text | Reuses 0–4s; does not search the whole tape |
| Slide book still building | `search_slides` anyway | Loop refuses: status ≠ ready | “not ready; look then answer” | `look` a short window, then `answer` |

If Gemma returns invalid JSON after a successful move, or hits 8 rounds, the loop stitches an answer from the steps instead of 422. Chat is allowed as soon as the **file** is `ready`; a `processing` book only blocks that search, not look/listen.
