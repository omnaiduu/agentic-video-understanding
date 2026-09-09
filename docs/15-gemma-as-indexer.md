# Gemma as indexer (discussion)

**Not v1. Not a locked phase.** The 13 phases still use four specialist phone books + E4B as the **reader**. This note records a later thread: when (and how) the **same** Gemma could also **find** times.

Related: [find vs understand](05-architecture.md) · [models](07-models-and-indexes.md) · [rejected: E2B as CLIP](04-what-we-rejected.md)

---

## 1. Two jobs (do not mix)

| Job | Question | Who |
|---|---|---|
| **Find** | Where in this 2-hour file should we open? | Indexes (`search` / `search_visual` / `search_audio` / `search_slides`) |
| **Answer** | What is true in that short slice? | Gemma on `look` / `listen` |

Indexes are a **map**. Gemma is the person who **opens the page**. Counting (“how many claps?”) is still **Python** on hits, not Gemma memory.

Chat Gemma (JSON, next-word) is job 2. Turning Gemma into an indexer means job 1: emit something **searchable**, once per file, not a paragraph per question.

---

## 2. Why chat Gemma cannot replace the four specialists

E4B **can** see and hear. Caps still apply: about **30s** of audio and about **60s** of video at 1 FPS per gulp. A 2-hour file is thousands of frames and hundreds of audio windows. Asking chat Gemma to hunt every question is a marathon.

| Specialist | What it caches once | What chat Gemma cannot cheaply replace |
|---|---|---|
| **Whisper** | Words + times | 2h transcript as ~240 generative 30s ASR calls, weak timestamps |
| **SigLIP 2** | 1 FPS stills as vectors | Skimming ~7,200 frames per question |
| **CLAP** | 3s sounds as vectors | Hearing 2h for a chirp or clap |
| **ColQwen2.x** | Unique slides as **patches** | Reading every slide when you do not know `t` |

Those four are not smarter than Gemma. They are **cheaper finders**. Gemma still **verifies** on a short slice. Second question must **not** rebuild them.

---

## 3. Two ways to make Gemma the finder

### Notes (no extra training)

Chop the file. Ask E4B to **write text** (transcribe 30s, list objects, name a sound, OCR a unique slide). Store `{time, text}`. Search with FTS + E5 like speech. Then `look` / `listen`.

This **is** Gemma as indexer. The index is a notebook. It is expensive: a 4B **generate** per slice. Fine for tens of unique slides. Painful for every 1 FPS frame or overlapping 3s audio hops. This is the `search_notes` anti-pattern if you caption **every** second.

### Vectors / fingerprints (the real indexer)

Stop generating. One forward pass. Save **numbers**. The question becomes numbers too. Closest numbers = the time.

How (mechanically):

1. Run Gemma on a slide / clip / 3s wav — **no** `generate()`.
2. Take last-layer hidden states.
3. Pool to one vector, **or** keep one short vector **per patch** (ColPali / MaxSim).
4. Train “close = same meaning” (contrastive / ColBERT). Raw chat states are **not** a search map until this step.

Ingest: vectors + timestamps into pgvector. Question: embed the user sentence → nearest `t` → LoRA off / chat Gemma `look`s.

**Notes** = sentences in a notebook. **Vectors** = a map you can query in milliseconds without writing a sentence per slice.

---

## 4. Four drawers vs one Gemma map

Both designs are “slow once, fast later.” Specialists are also cached. The change is **what you store** and **how many searches per question**.

**Today (locked):** four drawers — words, stills, sounds, slide patches. Gemma’s JSON **chooses** a drawer. You only hit several drawers when the question is vague, mixed, or the router guesses wrong — then glue times and hope `look` / `listen` fixes it.

**Unified Gemma space:** pay **more at ingest** (Gemma forwards on clips / slides / sounds). Each **question** can be **one** embed + **one** nearest-neighbor, then one or two short rewatches.

| Bill | Four specialists | One Gemma map |
|---|---|---|
| **Ingest** | Four small models; cheaper | 4B forwards; heavier |
| **Question** | 1–4 searches + maybe many `look`s | One search; fewer rummages if the map is good |

The bargain is **cheaper mixed questions**, not cheaper upload. Simple “what did she say about pricing?” should still be **one** Whisper search, not a giant cosine.

---

## 5. Why that map can be “richer” (and when it is not better)

SigLIP/CLAP are **phrasebooks**: short caption ↔ still, or tag ↔ 3s sound. One **global** vector per item. The JPEG is the **same point** for every later question. “Not” and “after” barely live in that text tower.

Gemma was trained to **guess the next word** given images, audio, and long text. Those hidden states can hold **grammar** (after, not, the other), **several senses in one sequence**, and **query-conditioned** pooling (attend to the **table**, ignore the product photo). ColPali-style: each query token picks a **patch** (MaxSim), so `$99` is not drowned in “looks like a slide.”

Toy geometry: bag-of-words CLIP can **prefer the product photo** because the query also said “photo.” Instruction-weighted patches can put **all** mass on the pricing table.

**Not automatically better.** Capacity ≠ index. Until contrastive/ColBERT training, nearest neighbor is noise. After training:

- Gemma used **like SigLIP** (short “a bird,” one still) → slower, often **worse** bird-finder.
- Gemma used as a **promptable clip / instruction / mixed-event** map → richer where the phrasebook is blind.

---

## 6. What a Gemma vector map is actually good at

Good = **one search, useful times**, then a short `look` / `listen`.

- **I don’t know which drawer** — “the important bit,” “when it went wrong.”
- **Two senses in one ask** — cheer + price on screen; alarm + someone stood up. This is the main product win vs gluing four lists.
- **Picky / long questions** — “after pricing, the **table** slide, not the product photo.”
- **Motion in a few seconds** — waved, shot, slide animated. SigLIP is one still; a **2–8s clip** vector can mean the action. (Index clips, not 7,200 full E4B stills.)
- **Slides** — **beats SigLIP** on printed text if you use **patches** (ColGemma / ColPali). Does **not** automatically beat ColQwen2.x on tiny fonts; that is a tie / small loss plus “one family.”

Speech **quotes** and **clap counts** are not this map’s job (need text and a sound-specific space). Those stay specialist or stay out of this note’s “well” list.

---

## 7. How to beat specialists in *some* areas (directions)

Do **not** replace first-stage 1 FPS / 3s hops with a 4B forward everywhere. Throughput still favors tiny encoders.

1. **Hybrid (highest accuracy for this loop)** — Specialists (or a cheap clip index) retrieve top ~50. Gemma `look` / `listen` **reranks**. That is already the architecture. Optimize routing and the rewatch before training an embedder.
2. **Video clip vectors where SigLIP is blind** — Index 2–4s (or scene-change) windows. Contrastive on video–caption / moment pairs. Eval on motion asks. If you don’t beat 1 FPS SigLIP there, the train failed.
3. **Instruction embed, not a second CLIP** — Query vector = `Represent a moment that matches: {full user question}`. Short-caption-only training yields a slower SigLIP.
4. **Domain LoRA** — Tens to hundreds of `(question, timestamp)` on *our* lectures/CCTV, hard negatives from the **same** file.
5. **Distill the query side** — Index documents with Gemma (once). Distill a ~70M text encoder to match Gemma **query** vectors so question-time stays specialist-fast (NanoVDR-style).
6. **Don’t bother** — Plain red light, clap, spoken words, `$99` with ColQwen already in plan: keep the drawers.

**Practical add-on, not a v1 swap:** keep four books; add **one** combined **clip** index for messy / motion / mixed asks; router sends simple channel questions to specialists and messy ones to the omni search; Gemma still only **opens** the door.

---

## Pointers

- [Gemma 4 model card](https://ai.google.dev/gemma/docs/core/model_card_4) — 30s audio / 60s video gulps
- [ColGemma4-E4B](https://huggingface.co/athrael-soju/ColGemma4-E4B-IT-Base) — ColPali recipe on E4B (slides)
- [ViLL-E](https://aclanthology.org/2026.acl-long.2003/) — VideoLLM embeddings vs SigLIP on composed / long queries
- [NanoVDR](https://arxiv.org/html/2603.12824) — distill VLM retrieval to a tiny query encoder
- [ColPali](https://arxiv.org/abs/2407.01449) — patch MaxSim vs OCR+text embed
