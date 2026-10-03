# Implementation plan

The app is built. Read [architecture](05-architecture.md) for the loop, [models](07-models-and-indexes.md) for the four indexes, and [implementation pass](13-implementation-pass.md) for where it runs.

[Build phases](12-build-phases.md) is the short record of what each slice added. Do not implement from the old 7-step skeleton (SQLite, 12B native tools, Vite-only).

**Done when:** from the website, a long video can (a) answer a speech question, (b) a silent visual, (c) a sound question, (d) “which slide had **Pro $99**?” when nobody said the number, (e) a follow-up without re-ingest, (f) show an exported clip **in the chat**, (g) work on a phone — without loading the whole file into Gemma. ColQwen finds the slide time; Gemma still reads the real frame.
