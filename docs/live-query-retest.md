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
