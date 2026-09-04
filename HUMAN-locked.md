# What you locked (for you)

You answered the holes. This is now the demo we build. Coding agents also read this plus `docs/20-backend-algorithm.md`.

---

## The ship

- **Node on your laptop.** Models on **Modal**. Deploy those models **from zero**.
- **One person** using it (you).
- Proof = **record a screen video**. Not a public website. Not login. Not a library of old chats.
- **Refresh the page → chat is gone.** No accounts. No “come back tomorrow.” The mp4 can still sit **on your disk**; pick it again. We may reuse books for the same file so we do not burn the GPU budget twice.

---

## What you can put in

- Add a video by **upload** or **URL** (a link to an **mp4**).
- **mp4 only.** You said **no size/time cap**. Honest note: a 3-hour file will still be **slow** and can blow a **$30** Modal month. The app will not refuse it; ingest will just take a long time.
- **English only** (speech and answers).
- **Audio-only** is OK (a sound file treated as a video with no picture). Slide/picture books may be empty; talk + sound still work.
- **One chat = one video.** Never two files in the same thread.

---

## Money and files

- About **$30 / month** GPU. **E4B only.** No 12B. Scale Modal to zero when idle.
- Original file lives **on your disk**. Node cuts with ffmpeg **on your disk**.
- Books (the four indexes) live on Modal for that ingest. Chat/sticky note live in **memory** for the session (gone on refresh).

---

## Models (locked)

- **Four books, including ColQwen** (slides). Required, not later.
- **Stay E4B.** If the form is weak, we do **not** swap in 12B.
- If search is empty: **“I couldn’t find it.”** Never guess.
- **Speaker labels on** (Speaker 1 / Speaker 2) for WhisperX. Needs extra work (pyannote). If it wrecks the $30 budget, we turn it off and tell you — default is **on** as you asked.

---

## The one page (desktop first)

One simple page. Phone can wait.

While it thinks: **spinner + live status** of what is happening, for example:

- searching speech…  
- searching slides…  
- cutting 8 seconds…  
- Gemma reading the frame…

That **is** the trace. You said “traces maybe” — we show this status to you on the demo. Not a secret debug dump.

When it answers, the page shows:

- the **text**
- **clickable times**
- a **quote from the transcript** (if it was a talk hit)
- the **frame(s)** Gemma actually looked at
- a **clip link** if you asked for a file

---

## Logic (unchanged, with your rules)

```
find time in a book  →  cut  →  look  →  answer  →  remember time
if nothing           →  say we couldn’t find it
refresh              →  chat gone
```

---

## Still not needed (defaults)

No public users, no YouTube-special downloader (URL means a **direct mp4 link**), no NSFW filter, no product name. If you later want YouTube-the-site, say so — that is extra and legally messy.
