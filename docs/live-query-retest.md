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

## What happens when you ask

Three pieces:

1. **You** type in the website chat.
2. **The laptop** (FastAPI) owns the video file, ffmpeg, and Postgres. It is the only thing that can cut frames or search.
3. **The model** (Gemma on a GPU) cannot open the file. It can only pick a next move: look, listen, search, export, or answer.

When you hit Send, the website sends your sentence to the laptop. The laptop asks the model: “what should I do?” The model answers with a move, not with the user-facing sentence yet. The laptop does that move, shows the model the result, and asks again. That repeats until the model says **answer**. Then the website shows that sentence in the bubble.

The model never watches the whole 16s tape at once. Look/listen cut a short slice **right now**. Search does not cut anything — it only looks up lists that ingest already stored (transcript lines, picture times, sound windows, unique slides).

### One full example: “Look at 0 to 2 seconds”

1. You type that and Send.
2. Laptop → model: here is the question; the file is 16s; indexes are ready.
3. Model → laptop: **look** from 0s to 2s.
4. Laptop runs ffmpeg on `original.mp4`, takes about two photos, sends those JPEGs to the model.
5. Model → laptop: **answer** “Pricing, Pro $99 per month.”
6. You see that sentence. Details shows `look 0s–2s` then `answer`.

### The other questions (same loop, different move)

**Look 0–4s**  
Same as above, four photos instead of two (one per second). Those photos are small (512px) so the GPU can hold them.

**Listen 0–6s**  
Model says **listen** 0–6s. Laptop cuts a short wav from the file and plays that clip to the model. Model answers what it heard (“Pro $99 a month”). It did not get the whole soundtrack.

**“What do they say about pricing?”**  
Model says **search** (speech book). Laptop finds matching Whisper lines in Postgres (here: 0.00s and 3.12s) and sends those short texts. Model answers from the lines. It still has not been shown the video.

**“Find the red alert screen”**  
Model says **search** the picture book. Laptop returns times that look similar (6s first). Times are not a photo, so the model then says **look** at 6–7s. Laptop takes that JPEG. Model reads “RED ALERT.”

**“Find the beep”**  
Same idea with the sound book: laptop returns time windows, model says **listen** at one of them, laptop cuts that wav, model answers “I heard a beep.”

**“Which slide had Pro $99?”**  
Model says **search slides**. Laptop asks the slide GPU to score “Pro $99” against the three unique slides, and gets a ranked list: 0s, 10s, 6s. That list is not the slide. Model says **look** at 0–1s. Laptop takes the JPEG. Model reads “Pro $99 per month” off that frame. If that frame had been red, it must say so — it is not allowed to copy $99 from your question onto the wrong photo.

**“Export a 4 second clip from 0s”**  
Model says **export**. Laptop writes a small mp4 to disk and tells the model a download URL. The model never gets the clip bytes. Your bubble shows the URL / player.

**“What was on that clip?”**  
Laptop reminds the model: last window was 0–4s. Model can **answer** from that memory. It does not search the whole tape again. Old photos are not sent a second time.

**Slide index still building**  
If the model tries slide search anyway, the laptop says “that book isn’t ready; look instead.” Model then **look**s at a short time (0–1s) and answers from the photo. Chat still works because the **file** is playable; only that search is blocked.
