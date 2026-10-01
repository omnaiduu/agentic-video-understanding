---
name: publish-to-omnaidu
description: Publish a post or demo clip to omnaidu.com through the private MCP. Use when Om asks to write a post, update a post, or upload a short demo video/image.
---

# Publish to omnaidu.com

This site has **no admin page**. You publish with MCP tools. Visitors never see that.

Owner: Om Naidu, Goa. Email **hello@omnaidu.com**. Dark-only hiring index. Content in D1, not git.

Live: https://omnaidu.com

## Connect MCP (Cursor)

You need the **omnaidu** MCP connected, with `PUBLISH_SECRET`. Use that name. Do not use **Lab** or **Lab2** if they fail discovery — delete them in the MCP list.

### Cloud Agents (phone app, desktop Cloud, this repo)

This skill is in **agentic-video-understanding**, so Cloud Agents on this repo load it.

MCP is not in git. Add it once at https://cursor.com/agents → **+** → **MCP Servers** → **Add MCP**:

- Type: **HTTP** (not OAuth)
- Name: `omnaidu`
- URL: `https://omnaidu.com/mcp`
- Header: `Authorization` = `Bearer <PUBLISH_SECRET>`

Then every new Cloud Agent on this repo (phone or desktop Cloud) gets the tools. This chat only sees servers that were already attached when it started.

### Desktop (local agent, not Cloud)

1. Copy `.cursor/mcp.json.example` to Cursor Settings → MCP (or `~/.cursor/mcp.json` / `.cursor/mcp.json` locally — never commit the real secret).
2. Replace `YOUR_PUBLISH_SECRET` with the Worker secret (`wrangler secret put PUBLISH_SECRET`).

```json
{
  "mcpServers": {
    "omnaidu": {
      "url": "https://omnaidu.com/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_PUBLISH_SECRET"
      }
    }
  }
}
```

The Worker also accepts `x-publish-secret`. If the server is missing, stop and say so — do not invent a publish UI or commit the post into git.

To reuse this skill on another machine, copy this folder to `~/.cursor/skills/publish-to-omnaidu/`.

Do **not**:
- Commit videos or posts into git
- Mention `/mcp` in public post copy
- Upload a huge camera file
- Restore light mode, RSS, or a Lab route
- Put a video on the homepage (home is poster-only)
- Add Exa as a public site-search box

## How to use the MCP tools

Call tools over JSON-RPC `POST https://omnaidu.com/mcp` (Cursor does this for you).

| Tool | When | Notes |
|---|---|---|
| `list_posts` | Before writing, to avoid duplicate slugs | Optional `tag` |
| `get_post` | Editing an existing slug | Includes drafts |
| `upload_media` | Images/video **before** `publish_post` | Base64 in JSON. Returns `/files/...` |
| `publish_post` | Create or update | Purges HTML + D1 caches |
| `unpublish_post` | Hide | Sets `status: draft` |
| `list_media` | Reuse an existing file | Recent R2 uploads |

Typical order: encode → `upload_media` (poster, then mp4) → `publish_post`.

Required on `publish_post`: `slug`, `title`, `abstract`, `body`, `tag`.

**Tags (exactly one):** `projects` | `research` | `systems` | `writing`

- `projects` — shipped work. Eligible for the homepage **Selected** slot (latest one).
- `research` — notes, math, papers.
- `systems` — infra, caching, workers, D1.
- `writing` — everything else.

Body is markdown. First `# title` is stripped. Lead video: `demoUrl` + `posterUrl`. Image-only lead: `posterUrl` only.

## Video limits

Hard caps are enforced on upload. Aim for the smaller numbers.

| What | Hard max | Aim for |
|---|---|---|
| File type | `.mp4` or `.webm` | **H.264 `.mp4`** |
| Length | **90 seconds** | **30–60s** |
| File size | **40 MB** | **2–8 MB** |
| Frame size | — | **720p** (1280×720) |
| Frame rate | — | 30 fps |
| Sound | — | Strip it (`-an`). Player starts muted |

The player does **not** download the MP4 until someone hits play. The page still downloads the **poster**. Home never embeds the video — only the still.

## Image limits

| What | Hard max | Aim for |
|---|---|---|
| Poster / photo | **8 MB** jpeg/png/webp/avif | **webp, 40–200 KB**, 1280×720 |
| Diagram | **512 KB** SVG | Small UTF-8 SVG |
| GIF | **4 MB** | Prefer a short mp4 |

Do **not** upload: phone originals, 4K, screenshots of code (use a fenced block), a video with no poster.

## How to process a demo (required)

On disk, before `upload_media`:

```bash
ffmpeg -i take.mov -an -c:v libx264 -pix_fmt yuv420p -r 30 -vf scale=-2:720 -movflags +faststart -crf 23 demo.mp4
ffmpeg -i demo.mp4 -ss 00:00:01 -frames:v 1 -vf scale=-2:720 poster.webp
```

If the mp4 is still over ~8 MB, raise `-crf` to 26 or cut the clip. Do not upload the `.mov`.

## How to upload a demo

1. Encode the clip and poster on disk.
2. `upload_media` for the mp4 (`contentType: video/mp4`).
3. `upload_media` for the poster (`contentType: image/webp` or `image/jpeg`).
4. You get `/files/uploads/....mp4` URLs.
5. `publish_post` with:
   - `demoUrl` = mp4 (top of the post is a video)
   - `posterUrl` = still (**required** if there is a video)
   - or only `posterUrl` for a picture at the top

If `demoUrl` is set, do **not** also paste `:::demo` of the **same** file in the body.

```md
:::demo{src="/files/uploads/….mp4" poster="/files/uploads/….webp"}
45s sandbox run.
:::
```

## Blocks (write these yourself — nothing auto-picks)

Fenced code with a language is highlighted. No `:::code`.

```rust
match intent {
    Intent::Balance => tools.balances(session).await?,
}
```

Languages that color: rust, ts/tsx, js, json, bash, python, go, sql, css, html, yaml, markdown, toml.

**Use often**

```md
:::callout{tone="note"}
Keep the contract in the tool schema, not the prompt.
:::

$E = mc^2$

:::figure{src="/files/uploads/….webp" alt="Loop diagram"}
Turn loop, one request at a time.
:::

:::proof{tests="142 passed" repo="https://github.com/omnaiduu/…"}
{"benches":[{"name":"p95","value":"12ms"}]}
:::

:::steps
1. Write the contract
2. Ship the loop
3. Put the receipt here
:::

:::theorem{title="Cache key"}
Worker version is in the key unless cross_version_cache is on.
:::

:::refs
RFC 9111
Cloudflare Workers Cache
:::
```

Callout tones: `note`, `warn`, `idea`, `result`, `danger`. Also `:::lemma` `:::definition` `:::proposition`.

**Use when needed**

```md
:::pullquote{cite="Om"}
Ship the system, then write the receipt.
:::

:::chart{kind="bar"}
[{"label":"before","value":120},{"label":"after","value":18}]
:::

:::details{summary="Edge cases"}
Empty slug is rejected.
:::

:::diff
- old header
+ new header
:::

:::filetree
{"name":"app","children":[{"name":"src","children":[{"name":"main.rs"}]}]}
:::

:::graph
{"nodes":[{"id":"a","label":"Worker","x":40,"y":80},{"id":"b","label":"D1","x":200,"y":80}],"edges":[{"from":"a","to":"b"}]}
:::

:::arch
[{"id":"w","label":"Worker"},{"id":"d1","label":"D1"},{"id":"r2","label":"R2"}]
:::

:::terminal{prompt="om@omnaidu"}
pnpm exec wrangler deploy
:::

:::timeline
[{"date":"Aug 16","title":"RSC + cache","detail":"Post bodies stay on the server."}]
:::

:::apispec{method="POST" path="/mcp" status="200" description="Private JSON-RPC"}
:::

:::compare{before="/files/a.webp" after="/files/b.webp" beforeCaption="Before" afterCaption="After"}
:::

:::kbd
⌘K
:::

:::desk
:::
```

`:::desk` is the 2D laptop. Only on a post about this site.

`:::hero{src poster}` is an in-body lead. Prefer `demoUrl`/`posterUrl` on the post instead of duplicating it.

## Shape of a good post

1. Problem
2. What you tried
3. What you shipped
4. How you checked it (tests / numbers)
5. Short demo or a figure

Do not write a YouTube script. Keep it readable. Dark OG card is generated from title + abstract at `/og/{slug}.png` (1200×630 PNG for WhatsApp, X, LinkedIn).

## Design reminders while writing

Omnaidu site: dark only. Quiet type. Selected work then the list. No Lab route, no RSS, no light mode.
