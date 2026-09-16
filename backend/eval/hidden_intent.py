"""Same hidden-intent questions E4B already ran. Not an answer key.

The laptop still does not hardcode beep / clap / ship / $99.
Gemma still picks look / listen / search / search_visual / search_audio /
search_slides / export / answer. This file only lists the questions and
what E4B actually did, so a later 12B run can use the same wording.
"""

from __future__ import annotations

from typing import TypedDict

# Leftover live suite. Same eight prompts as the Modal E4B reruns.
QUESTIONS: list[tuple[str, str]] = [
    ("E1", "How much does Pro cost?"),
    (
        "H1",
        "I think the $99 price is on the red emergency screen — can you confirm?",
    ),
    ("M3", "What are we supposed to ship this quarter?"),
    (
        "M4",
        "When does the notification tone play, and what is on screen at that moment?",
    ),
    (
        "M1",
        "They said a number is also printed on the slide. What color is that number, "
        "and does it match what they said?",
    ),
    ("H5", "How many claps are in this recording?"),
    (
        "H7",
        "Make a three-second clip of whatever is on screen when the beep happens.",
    ),
    (
        "H8",
        "Walk through the whole tape in order, including things nobody said out loud.",
    ),
]


class E4BNote(TypedDict):
    verdict: str
    what_happened: str
    fragile_crutch_we_removed: str
    what_12b_should_try_without_a_bounce: str


# Honest E4B scoreboard. Not a claim that 12B will pass.
E4B_OBSERVATIONS: dict[str, E4BNote] = {
    "E1": {
        "verdict": "pass",
        "what_happened": "Opened spoken words. Answered $99 a month.",
        "fragile_crutch_we_removed": "none",
        "what_12b_should_try_without_a_bounce": "Same question. Speech or a look at Pricing is enough.",
    },
    "H1": {
        "verdict": "unstable",
        "what_happened": (
            "Sometimes looked at Pricing, red, and Q3 and said the price is not on red. "
            "Sometimes led with Yes (the trap) even after seeing $99 on navy."
        ),
        "fragile_crutch_we_removed": "none — there was never an H1 laptop rule",
        "what_12b_should_try_without_a_bounce": (
            "Reject the false premise from the pixels. Do not add a 'say no' bounce."
        ),
    },
    "M3": {
        "verdict": "pass",
        "what_happened": "Speech missed the never-spoken heading, then slides + look at Q3.",
        "fragile_crutch_we_removed": "none",
        "what_12b_should_try_without_a_bounce": "Still leave speech when it does not answer; look at the printed slide.",
    },
    "M4": {
        "verdict": "pass_with_hint",
        "what_happened": (
            "Sound hit 9–12s. Then look+listen near the middle (10.5–12.5). "
            "Named Q3 / Ship the slide index. The observe note used to say "
            "'cut from the middle'."
        ),
        "fragile_crutch_we_removed": (
            "Prompt that told it to look/export at the middle of a CLAP window."
        ),
        "what_12b_should_try_without_a_bounce": (
            "Listen inside the 9–12s hit, then say what is on screen at the tone."
        ),
    },
    "M1": {
        "verdict": "fail_without_bounce",
        "what_happened": (
            "Looked at Q3, Pricing, and red. Named yellow $99. Then answered "
            "without searching speech: cannot confirm a match. With a bounce that "
            "blocked answer until search, E4B passed (yellow 99 matches spoken $99)."
        ),
        "fragile_crutch_we_removed": (
            "Keyword bounce on 'printed' + 'they said': block answer until a forced "
            "speech search, then a 'compare the lines' note."
        ),
        "what_12b_should_try_without_a_bounce": (
            "Open both books on its own: look at the printed number, search speech, "
            "then say whether they match."
        ),
    },
    "H5": {
        "verdict": "fail",
        "what_happened": (
            "Sound search is not a clap detector. E4B treated hit rows as a count, "
            "or listened to silence/tone and said one clap. An 'if unsure, say zero' "
            "bounce was exam-shaped and was already removed."
        ),
        "fragile_crutch_we_removed": "unsure → zero bounce (already gone)",
        "what_12b_should_try_without_a_bounce": (
            "Listen at a hit. If the wav is not claps, say zero. Still no laptop clap counter."
        ),
    },
    "H7": {
        "verdict": "fail_without_recut",
        "what_happened": (
            "search_audio returned a similar-audio RANGE (often 9–12s). E4B exported "
            "that whole range without listening. The start of the window is the previous "
            "slide. Recut-from-middle then extra-export-cap made a later live pass "
            "(9–12 then 10.5–12.5). Without that crutch, exporting the range is the bug."
        ),
        "fragile_crutch_we_removed": (
            "Laptop recut-from-middle (~2s from the hit midpoint), bounce answers until "
            "that recut, and block further exports."
        ),
        "what_12b_should_try_without_a_bounce": (
            "search_audio → listen at a hit → export only the range it heard. "
            "If it still dumps the whole CLAP window, that is a 12B fail, not a reason "
            "to put the recut bounce back."
        ),
    },
    "H8": {
        "verdict": "pass_with_skip",
        "what_happened": (
            "2s look+listen crawl burned 12 moves by ~9s until skip-ahead blocked the "
            "next 2s step when >6s remained (look-only too). Then it named Pricing, "
            "RED ALERT, and Q3."
        ),
        "fragile_crutch_we_removed": "none — skip-ahead stays; it is loop hygiene, not a prompt guess",
        "what_12b_should_try_without_a_bounce": (
            "Search then jump, or skip 2s crawls. Same skip-ahead rule is still on."
        ),
    },
}


def question_ids() -> list[str]:
    return [qid for qid, _text in QUESTIONS]
