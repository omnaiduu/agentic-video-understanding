# The rest of the notes, in plain words

The blog tells the main story: why the model fills a form, why there are four lists, and what happened when a bigger model and “thinking” were tried on the same setup.

This page is the rest. Same 16-second video. Someone says the pro plan is $99. That number is also printed on a dark blue slide. Then the screen is red and quiet. Then a slide says “ship the slide index,” which nobody says out loud. A short beep plays around 11 seconds. There are no claps.

---

## If the question sounds like someone said it

Some questions sound like speech even when the answer is not spoken.

“What are we supposed to ship this quarter?” The words are only printed on the last slide. The model searched what was said, found the $99 line, and stopped.

“Make a clip of when the beep happens.” It searched the word “beep” in the speech list and cut the price slide. The beep is a sound, not a word.

What changed: after one speech search, the code says those lines are only what was spoken. It does not search speech a second time for the same question. The model then has to try something else.

After that, “what do we ship this quarter?” went to the slides, looked at the last slide, and read “ship the slide index.” The beep question opened the sound list. The clip was still 9 to 12 seconds, so it starts on the red screen. That part is a different problem. A sound hit is about 3 seconds, not the exact moment.

Easy questions stayed easy. “How much does Pro cost?” still comes from speech.

---

## Helpers that made this video pass, then came off

Before comparing the small model with the bigger one, three helpers were removed. They only helped this one video.

1. If the cut matched the whole sound hit, cut again from the middle. The beep happened to sit near the middle of a 3-second chunk. A beep at the start of the next chunk would be cut off. The computer cannot hear the file. The helper was guessing.

2. If the question said “printed” and “they said,” do not accept an answer until speech was searched. The next way of asking the same thing would miss those words.

3. If the model was not sure how many claps, tell it to say zero. This video has zero claps, so the test went green. A video full of claps could go green for the wrong reason.

The bigger-model test ran without these three. One rule stayed. Asked to walk through the whole video, the model looked two seconds at a time. Each look uses one of twelve moves. It ran out of moves before the last slide. It was moving. It was moving in tiny steps. If a lot of the video is still left, another two-second step is blocked, and it has to jump ahead. That rule is about the move limit. It does not know where the beep is.

---

## What stays unfinished

- The small model can still cut 9 to 12 seconds for the beep, without listening. The clip then starts on the red screen.
- “How many claps?” is not a real count. Search hits that sound a bit like a clap are not claps. A bigger model invented five. The next step, if counting matters, is a detector on the audio. A bigger model did not fix it.
- “Is the $99 on the red screen?” can still start with “yes,” even when the rest of the sentence is right.
- The times from this video are not written into the code. There is no rule that says beep means second 11, or that an unsure count is zero.
