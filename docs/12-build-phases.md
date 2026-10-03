# Build phases

This is one production app, built in slices. ColQwen2.x + `search_slides` is part of this app.

| Read this | For |
|---|---|
| [01 Goal](01-goal-and-context.md) | What the product is |
| [03 Key decisions](03-key-decisions.md) | Locked product choices |
| [05 Architecture](05-architecture.md) | Ingest vs question loop |
| [06 Tools](06-tools.md) | Action list and limits |
| [07 Models](07-models-and-indexes.md) | Gemma, Whisper, SigLIP, CLAP, ColQwen |
| [08 Frontend/backend](08-frontend-backend.md) | Stack |
| [13 Implementation pass](13-implementation-pass.md) | Libraries, Modal/GPU, size |

Upload a long video. Indexes are built once (speech, pictures, sounds, slides). Ask a question. Gemma names a step on a short slice. The answer has a timestamp, and sometimes a clip. A second question does not rebuild the indexes.

| Slice | What it added |
|---|---|
| 1 | FastAPI + Postgres + save the file + duration |
| 2 | `get_meta` / `get_frames` / `get_audio`, with limits |
| 3 | Gemma JSON loop, `/chat` |
| 4 | Whisper speech index on Postgres |
| 5 | SigLIP 2 + `search_visual` |
| 6 | CLAP + `search_audio` |
| 7 | `export_clip` / `export_audio` + a URL |
| 8 | Last timestamps across turns in a session |
| 9 | TanStack Start website shell |
| 10 | Upload in the browser, live index status |
| 11 | Video.js, chat, seek |
| 12 | Clip in the chat, phone layout, delete |
| 13 | Unique slides + ColQwen2.x + `search_slides` |

vLLM JSON schema, not native `tools=`. Speech search is keyword plus dense retrieval on Whisper lines. Picture search is SigLIP 2 at about 1 FPS. Sound search is LAION-CLAP on 3-second chunks. Export longer than 60 seconds is refused. The website is TanStack Start. ColQwen finds a slide time. Gemma still reads the frame.
