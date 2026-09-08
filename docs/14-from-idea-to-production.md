# From idea to production (without reading code)

A playbook for a human who will **not** open the source. Agents write the software. You still need a production app that feels like a careful person built it: reliable, small, reversible.

This file is the **method**. This repo’s [phase map](12-build-phases.md) and [implementation pass](13-implementation-pass.md) are one **instance** of the method.

You do not need to learn a language (Go, Python, TypeScript) before you start. You need to be willing to lock contracts, run checks, and ask **how** the code will be written — options, why this way, what it solves — before an agent implements a phase.

---

## The job, in one sentence

You own three things: the **contract** (what is true), the **check** (how you will know), and the **stop** (when the agent must ask). The agent owns everything between those.

“Written by a human” is not a writing style. It is:

- one fact lives in **one** place
- pieces stay **small**
- mistakes show up in a **test or a command**, not in a user’s face
- no library appears because it was the model’s **habit**

Vibe coding is not “AI wrote it.” Vibe coding is **accepting output you had no way to verify.**

---

## What you own vs what you hand over

| You lock (even if you never open a file) | Agent may do without asking |
|---|---|
| Who uses it, what they do, what they get back | Names of functions and files (inside the size budget) |
| Request / response / error for every action | Filling in those shapes |
| What is stored, what is deleted | SQL, folders, ffmpeg flags |
| Limits (file size, frames, clip length, GPU spend) | Enforcing the numbers you locked |
| When a wrong choice would show up | Tests that encode that |
| Go / no-go to the next phase | The code for **this** phase only |

If you skip the left column, the agent fills it with defaults. That is how Tailwind, React Query, or an A100 appear without a conversation. The miss is not “the agent used a library.” The miss is **the agent was allowed to treat a habit as a decision.**

---

## Eight stages (do them in order)

Do not ask an agent to “build the app” on day one. Walk these stages. Code starts at stage 5, and only for **one phase**.

```
0 idea     → 1 boxes    → 2 contracts → 3 decisions
4 phases   → 5 loop     → 6 reliability → 7 deploy
```

---

### Stage 0 — Freeze the idea (you, one sitting)

Write these in **your** words. A planning agent may tidy them. You lock them.

1. **One paragraph.** Who, what they do, what they get back. Not “an AI video platform.” Something like: “A person uploads a two-hour talk, asks where the red slide was, and the player jumps there.”
2. **Five journeys.** One happy path. Four failures (file too big, no audio, model down, user deletes). Failures are product. If you skip them, the agent invents 500 error pages — or none.
3. **Out of scope.** Tempting extras you will not build. This is how a complicated app stays **one** app.
4. **Done, as something you can see.** “I can upload, wait until status is ready, ask a question, click a timestamp.” Not “the architecture is solid.”

Paste this to a planning agent:

> Restate this product in your own words. List what is still ambiguous. Do **not** suggest libraries, frameworks, GPUs, or folders yet. If you cannot restate it, ask me questions until you can.

If the agent answers with React, stop. It is not doing this stage.

---

### Stage 1 — Boxes, not code

Ask for a sketch with **boxes and arrows**, not classes.

- Who talks to whom
- What is stored (files, rows, vectors)
- What happens **once** (ingest) vs **every question** (the loop)
- What costs money (GPU, disk)

Enough boxes for this video app were: file store, API, three indexes, brain, website. That is a system. That is not code.

Questions:

- If I turn **this** box off, what still works?
- Which boxes share a GPU? (Shared small GPU → chat dies while indexing.)
- Which fact lives in two boxes? (That is a future lie.)

---

### Stage 2 — Contracts before bricks

For every user action, lock three things:

- **In:** what is sent (file, JSON, id)
- **Out:** what comes back on success **and** on error (status, body)
- **Limit:** 2 GB, 64 frames, 60 seconds, whatever the number is

This is the type-safety conversation without the word TypeScript.

A **contract** is a promise between parts. Types, OpenAPI, and tests are how the computer keeps the promise. You care about the promise. You do not need to care which file holds the types — you **do** need to care that the website does not invent a second copy of the promise by hand.

Ask:

- Write the HTTP call and the JSON for this action, including the error body.
- Where is this number written **once**?
- If the website and the API disagree, **who wins?**
- Is the shape checked when the request arrives, or only when a human sees a crash?

Do **not** ask “should we use Pydantic / Zod / React Query.” Those names are answers. Ask when you find out.

---

### Stage 3 — Decisions as consequences (the habit that was missing)

Never: “Should we use React Query?”

Always: “When the list is already on screen, do we show the old list while it refreshes, or a spinner every time?”

Every library is a **bet on a behavior**. If the agent cannot say the behavior, it does not understand the library either — and you cannot judge it.

**Five lines, before any code:**

| Line | Example |
|---|---|
| What | PostgreSQL, not SQLite |
| Alternative | A SQLite file |
| If this is wrong, when do I find out? | First concurrent upload — or never |
| Cost to reverse | A migration, or one file |
| Default, or reasoned from the spec? | Reasoned: we need `pgvector` later |

Then ask the question that catches silent defaults:

> Which of these did you pick because it is your default, not because something in the spec required it?

**Cheap vs expensive.** Spend your attention on the expensive column.

| Cheap — let the agent do it | Expensive — you lock |
|---|---|
| Variable names, CSS class names | Database, “brain fills a JSON form, we run tools” |
| Test helper files | GPU type, one box vs two |
| Exact ffmpeg flags (caps still hold) | Delete semantics, secrets, CORS, money |

Software engineering, for you, is mostly: **put each choice in the cheap or expensive bucket, then lock the expensive ones in behavior language.**

---

### Stage 4 — Cut into phases

A phase is **one new thing a stranger can observe**. It is not a “v1 of the product.”

| Good phase | Bad phase |
|---|---|
| Store a file and return duration | “First version of the app” |
| Cut frames under a cap | “Make scissors and also chat” |
| Website shell that lists videos | “The whole frontend” |

Rules:

- **Backend contracts first, UI second.** UI on a moving contract is rewrite hell. You feel that as “the agent keeps breaking the page,” not as a stack choice.
- Each phase has a **check** you can run without opening a file (`curl`, a test name, a 20-second recording).
- Each phase says what it must **not** do (no Whisper in “hold a file”).
- **Size budget:** a handful of new files, about 200–300 lines each. If it needs more, the phase is too big or the agent is generating a novel.
- **One phase in flight.** One branch. One PR. When a check fails, there is only one place it came from.

Ask:

> Split this into the smallest phases that still lead to **one** production app. For each: one sentence of new capability, the check I will run, what is forbidden, what later phases will plug into. No libraries yet unless a phase cannot exist without naming one (ffmpeg, Postgres).

---

### Stage 5 — The daily loop (this is the workflow)

For **every** phase, in this order. Do not skip 3 or 7.

1. **Card.** Planning agent writes: capability, check, forbidden work, allowed libraries (maybe none), five-line decisions.
2. **You lock** — or you ask “default or reasoned?”
3. **Fresh review.** A **new** agent with **no** memory of the plan: “What did the planner assume? What will bite us? Which libraries were not earned?” Same-context agents agree with themselves. That is not a review.
4. **Implement.** Coding agent follows the card. Turns the check into a test. Adds **no** library that is not on the card.
5. **You verify behavior.** One command, or one short recording. You are not judging the diff. You are judging the check.
6. **Review agent on the diff** (you read the summary): new dependency? file over ~300 lines? test weakened? cap changed? delete path different from the card?
7. **Pain report** from the coding agent: “What did you write more than twice? What felt fragile? What did you work around? What would you refactor if I let you?”
8. **Merge. Next phase.** If the check failed, there is no next phase.

The pain report is how **you** feel the pain a library is supposed to encode. When the agent says “I copied the same loading/error fetch in four screens,” *that* is when a query library is earned — not on day one because it is popular.

If the same bug is fixed twice, the spec is wrong. Change the card. Do not ask for another coding attempt on the same card.

---

### Stage 6 — Reliability (the “human” bar)

Agents write code that looks finished and fails like a prototype. You prevent that **without reading** by insisting on:

- **One source of truth.** Caps in one place. Client types **generated** from the API schema, not typed again by hand. Hand-copied types are how “no type safety” actually happens — two promises, they drift, nobody notices until a user does.
- **Boring over novel.** A fancy library needs a pain report, not a blog post.
- **Errors as product.** Every failure journey from stage 0 has a sentence the user can read.
- **Delete and money are in the card.** The agent does not improvise “rm -rf” or GPU hours.
- **Small files.** A 2,000-line module is an agent that could not stop. Complexity is hiding.

Ask, before you call a phase done:

> If a senior engineer joined tomorrow and was only allowed to read the phase cards and the checks, could they operate this app in their head? If not, the docs are the bug — fix them before more code.

---

### Stage 7 — Deploy without opening the repo

Deploy is another contract, not a vibe.

Lock, in commands you will type:

- **Start:** one command, or one Modal deploy
- **Health:** a URL that must say ok
- **Rollback:** previous revision, one command
- **Secrets:** not in git; where they live
- **Cost:** scale-to-zero; a spend cap if the host has one
- **Logs:** a place you can read “upload failed” without SSH
- **Death halfway:** process killed mid-ingest → status is `error` or a job retries, never a silent ghost file

Ask:

> Write the runbook as commands I will type and the output I should see. Include GPU out of memory, disk full, and a bad secret. Do not paste source.

You ship when **you** ran the runbook, not when the agent said “deployed.”

---

### Stage 8 — Keep it from rotting

After each phase, and again before you call the app production:

- Fresh agent, docs only: “Explain how a question is answered. Where can this lie to the user?”
- You (or a browser agent you instruct): walk the five journeys
- Repeated pain-report lines → now you **approve** a library or a split, because the pain is real

---

## Questions that reach the bottom (steal these)

Paste the relevant block whenever an agent is about to “just implement.”

**Product**

- Who is in a hurry, and what do they do first?
- What does failure look like to **them**?
- What are we not building, even if it would be cool?

**Truth**

- If this is wrong, when do I find out — at build, in a test, when a user hits it, or never?
- Is this fact written down twice?
- If two parts disagree, who wins?

**Shape**

- What is the boring default, and what does the fancy one buy me?
- If we change our mind, is it one file or the whole app?
- Which of these did you pick by default?

**This phase**

- What is forbidden in this slice?
- What check will I run, in one command or one recording?
- Name every new library. For each: which line in a pain report earned it?

**Harm**

- What deletes data?
- What spends GPU or money while I am asleep?
- What happens if the process dies halfway?

**After code exists**

- What did you write more than twice?
- What did you work around?
- What would you refactor if I let you — and why is that not a new phase yet?

---

## What to paste every phase (how the code is written)

You do **not** need to learn Go (or any language) first. You need this round **before** the agent writes the phase — same as product questions, but for *how*.

Paste:

```
This phase only. Do not write the app yet.

1. What are 2 or 3 ways to write this, used in 2026 for this stack?
   Search. Do not guess from memory.

2. For each way:
   - What problem does it solve?
   - What still breaks if we use it?
   - What is the simpler alternative?
   - Why would you pick it vs the others?

3. Which of these is your habit / default, not required by the spec?

4. What check proves the winner? (one command or one short recording)

Stop. I will lock one way. Then you implement only that.
```

After it built the phase, paste:

```
Why did you write it this way?
What other way did you skip?
If I skip the library/pattern you used, what bug appears?
Show that bug on a tiny example if you can.
Did you add anything not on the card?
```

Do not ask “what’s best” or “production-ready.” Ask **options, what it solves, why this, what you skipped.**

---

## What to avoid

| Avoid | Do instead |
|---|---|
| “Build me the app” | Stage 0 paragraph + five journeys |
| “Use best practices / production-ready” | Five-line decision |
| Library name as the first question | Behavior that library buys |
| Reading the diff to decide if it is good | Run the check |
| Same agent plans and reviews | Fresh agent, empty context |
| UI first | Contract first |
| A giant phase | One observable job |
| “A small helper library” | Stop and ask |
| Weakening a test so CI is green | Fix the spec or the bug |
| Next phase while this check fails | Stop |
| Shipping because the agent said done | You run the runbook |

---

## Standing prompt (paste at the start of every planning chat)

```
You are planning with a human who will not read the source.

Do not suggest a library, framework, or GPU until you can say:
1. the behavior it buys
2. the plain alternative
3. when we find out if the choice is wrong
4. cost to reverse
5. whether this is your default or reasoned from the spec

Do not start coding. Write a card: capability, check I can run,
forbidden work, allowed libraries (maybe none), five-line decisions.

Ask me in behavior terms, not jargon. Flag anything you were
about to pick by habit.
```

**Standing prompt for a coding agent** (after the card is locked):

```
Implement only this card. Do not add a library that is not listed.
If a file grows past ~300 lines, split it. Turn the check into a test.
Do not weaken tests. When you finish, write a pain report:
what you wrote twice, what felt fragile, what you worked around.
If you need a decision that is not on the card, stop and ask.
```

**Standing prompt for a review agent** (fresh chat, paste the card + the diff summary the coding agent produced):

```
You did not write this plan. Attack it.
What was assumed? Which libraries were not earned?
What will bite us in the next phase? What deletes or spends money
without a check? Do not rewrite the code. List risks.
```

---

## How you comprehend the system (without code)

You understand the app when you can answer these from **docs and checks only**:

- What a user can do, and what they cannot
- What each phase added, and what it was forbidden to add
- What command proves a phase
- What we refused, and why
- What costs money
- What deletes files

If you cannot answer, the agent wrote software **you do not own**. Fix the cards before you ask for more code. That *is* software engineering in this workflow: judgment over contracts, not taste over syntax.

---

## This repo, as an example of the method

Product stages 0–4 were done in docs 01–12 (journeys, boxes, phases, locked behavior). [Doc 13](13-implementation-pass.md) is now **locked** (laptop API, Modal models, L4, slices only, live ingest UI). Use **this file** as the method for any new idea; use 12 and 13 when you implement **this** idea. First code is Phase 1 only.
