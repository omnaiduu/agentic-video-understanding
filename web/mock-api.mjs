#!/usr/bin/env node
/**
 * UI demo API that matches the FastAPI contract enough to exercise the website
 * without Postgres, Modal, or Gemma. Not the production backend.
 */
import { spawnSync } from "node:child_process"
import { randomUUID } from "node:crypto"
import fs from "node:fs"
import http from "node:http"
import path from "node:path"
import { fileURLToPath } from "node:url"

const PORT = Number(process.env.MOCK_API_PORT || 8000)
const HOST = process.env.MOCK_API_HOST || "127.0.0.1"
const DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), ".mock-media")
const SRC_DIR = path.join(DIR, "src")
const SAMPLE_WAV = path.join(DIR, "sample.wav")
const MAX_UPLOAD = 2 * 1024 * 1024 * 1024
const BOOKS = ["transcript_status", "visual_status", "audio_status", "slides_status"]

fs.mkdirSync(DIR, { recursive: true })
fs.mkdirSync(SRC_DIR, { recursive: true })

const BROLL = [
  {
    id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    file: "broll-flower.mp4",
    name: "Greenhouse flower.mp4",
    url: "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
    start: 0,
    duration: 5,
    created_at: "2026-04-08T12:00:00Z",
  },
  {
    id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    file: "broll-railway.mp4",
    name: "Mountain railway.mp4",
    url: "https://upload.wikimedia.org/wikipedia/commons/transcoded/8/87/Schlossbergbahn.webm/Schlossbergbahn.webm.480p.vp9.webm",
    start: 0,
    duration: 10,
    created_at: "2026-06-12T09:00:00Z",
  },
  {
    id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
    file: "broll-meadow.mp4",
    name: "Meadow light.mp4",
    url: "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4",
    start: 0,
    duration: 10,
    created_at: "2026-07-02T15:30:00Z",
  },
  {
    id: "dddddddd-dddd-dddd-dddd-dddddddddddd",
    file: "broll-pass.mp4",
    name: "Snow pass.mp4",
    url: "https://media.w3.org/2010/05/sintel/trailer.mp4",
    start: 8,
    duration: 10,
    created_at: "2026-08-19T18:10:00Z",
  },
]

function probeDuration(filePath) {
  const probed = spawnSync(
    "ffprobe",
    ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", filePath],
    { encoding: "utf8" },
  )
  const value = Number(probed.stdout)
  return Number.isFinite(value) ? value : 8
}

function transcode(src, dest, start, duration) {
  const common = [
    "-y",
    "-ss",
    String(start),
    "-i",
    src,
    "-t",
    String(duration),
    "-vf",
    "scale=1280:-2",
    "-c:v",
    "libx264",
    "-pix_fmt",
    "yuv420p",
    "-preset",
    "veryfast",
    "-crf",
    "23",
    "-movflags",
    "+faststart",
  ]
  const withAudio = spawnSync(
    "ffmpeg",
    [...common, "-c:a", "aac", "-b:a", "128k", "-ac", "2", "-ar", "44100", dest],
    { stdio: "ignore" },
  )
  if (withAudio.status === 0 && fs.existsSync(dest)) {
    return
  }
  spawnSync("ffmpeg", [...common, "-an", dest], { stdio: "ignore" })
}

function download(url, dest) {
  const got = spawnSync("curl", ["-fsSL", "--max-time", "90", "-o", dest, url], {
    stdio: "ignore",
  })
  return got.status === 0 && fs.existsSync(dest) && fs.statSync(dest).size > 1000
}

function ensureClip(clip) {
  const dest = path.join(DIR, clip.file)
  if (fs.existsSync(dest) && fs.statSync(dest).size > 1000) {
    return dest
  }
  const src = path.join(SRC_DIR, path.basename(clip.url))
  if (!fs.existsSync(src) || fs.statSync(src).size < 1000) {
    if (!download(clip.url, src)) {
      throw new Error(`could not download B-roll ${clip.name}`)
    }
  }
  transcode(src, dest, clip.start, clip.duration)
  if (!fs.existsSync(dest) || fs.statSync(dest).size < 1000) {
    throw new Error(`ffmpeg could not write ${clip.file}`)
  }
  return dest
}

function ensureMedia() {
  for (const clip of BROLL) {
    ensureClip(clip)
  }
  if (!fs.existsSync(SAMPLE_WAV)) {
    spawnSync(
      "ffmpeg",
      ["-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=3", SAMPLE_WAV],
      { stdio: "ignore" },
    )
  }
}

ensureMedia()

function publicVideo(row) {
  const { filePath, startedAt, ...rest } = row
  void filePath
  void startedAt
  return rest
}

function applyIngest(row) {
  if (row.status !== "processing") {
    return row
  }
  const elapsed = (Date.now() - row.startedAt) / 1000
  const completed = Math.min(BOOKS.length, Math.floor(elapsed / 1.15))
  for (let i = 0; i < BOOKS.length; i += 1) {
    if (i < completed) {
      row[BOOKS[i]] = "ready"
    } else if (i === completed) {
      row[BOOKS[i]] = "processing"
    } else {
      row[BOOKS[i]] = "pending"
    }
  }
  if (completed >= BOOKS.length) {
    row.status = "ready"
    for (const key of BOOKS) {
      row[key] = "ready"
    }
  }
  return row
}

function makeVideo(partial) {
  const id = partial.id || randomUUID()
  return {
    id,
    original_filename: partial.original_filename || "video.mp4",
    path: `/data/videos/${id}/original.mp4`,
    kind: partial.kind || "video",
    duration_s: partial.duration_s ?? 8,
    fps: 30,
    has_audio: partial.has_audio ?? true,
    has_video: partial.has_video ?? true,
    status: partial.status || "ready",
    transcript_status: partial.transcript_status || "ready",
    visual_status: partial.visual_status || "ready",
    audio_status: partial.audio_status || "ready",
    slides_status: partial.slides_status || "ready",
    error_message: null,
    created_at: partial.created_at || new Date().toISOString(),
    filePath: partial.filePath,
    startedAt: partial.startedAt || Date.now(),
  }
}

const videos = new Map()
const exportsStore = new Map()

for (const clip of BROLL) {
  const filePath = path.join(DIR, clip.file)
  videos.set(
    clip.id,
    makeVideo({
      id: clip.id,
      original_filename: clip.name,
      duration_s: probeDuration(filePath),
      created_at: clip.created_at,
      filePath,
    }),
  )
}

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
  "Access-Control-Allow-Headers": "*",
  "Access-Control-Expose-Headers": "Accept-Ranges, Content-Range, Content-Length",
}

function json(res, status, body) {
  const payload = JSON.stringify(body)
  res.writeHead(status, {
    ...CORS,
    "Content-Type": "application/json",
    "Content-Length": Buffer.byteLength(payload),
  })
  res.end(payload)
}

function sendFile(req, res, filePath, contentType) {
  if (!fs.existsSync(filePath)) {
    json(res, 404, { detail: "Not found" })
    return
  }
  const size = fs.statSync(filePath).size
  const range = req.headers.range
  if (range) {
    const match = /bytes=(\d*)-(\d*)/.exec(range)
    const start = match?.[1] ? Number(match[1]) : 0
    const end = match?.[2] ? Number(match[2]) : size - 1
    const safeEnd = Math.min(end, size - 1)
    res.writeHead(206, {
      ...CORS,
      "Content-Type": contentType,
      "Content-Range": `bytes ${start}-${safeEnd}/${size}`,
      "Accept-Ranges": "bytes",
      "Content-Length": safeEnd - start + 1,
      "Content-Disposition": "inline",
    })
    fs.createReadStream(filePath, { start, end: safeEnd }).pipe(res)
    return
  }
  res.writeHead(200, {
    ...CORS,
    "Content-Type": contentType,
    "Accept-Ranges": "bytes",
    "Content-Length": size,
    "Content-Disposition": "inline",
  })
  fs.createReadStream(filePath).pipe(res)
}

async function readBody(req) {
  const chunks = []
  for await (const chunk of req) {
    chunks.push(chunk)
  }
  return Buffer.concat(chunks)
}

function parseMultipart(buffer, contentType) {
  const boundMatch = /boundary=(?:"([^"]+)"|([^;]+))/i.exec(contentType || "")
  const boundary = boundMatch?.[1] || boundMatch?.[2]
  if (!boundary) {
    return null
  }
  const token = Buffer.from(`--${boundary}`)
  let start = buffer.indexOf(token)
  while (start !== -1) {
    const headerStart = start + token.length + 2
    const headerEnd = buffer.indexOf(Buffer.from("\r\n\r\n"), headerStart)
    if (headerEnd === -1) {
      break
    }
    const headers = buffer.subarray(headerStart, headerEnd).toString("utf8")
    const next = buffer.indexOf(token, headerEnd)
    if (next === -1) {
      break
    }
    const dataEnd = next - 2
    const filename = /filename="([^"]+)"/.exec(headers)?.[1]
    if (filename) {
      return {
        filename,
        data: buffer.subarray(headerEnd + 4, dataEnd),
      }
    }
    start = next
  }
  return null
}

function audioName(name) {
  return /\.(mp3|wav|m4a|aac|flac|ogg|opus)$/i.test(name)
}

function chatReply(message, row) {
  const q = message.toLowerCase()
  const session_id = randomUUID()
  const videoId = row.id
  if (/ten minutes|600|too long|hour/.test(q)) {
    return {
      answer: "Need a shorter window.",
      citations: [],
      steps: [
        {
          do: "export_clip",
          start_s: 0,
          end_s: 600,
          ok: false,
          detail: "requested 600.000s export; cap is 60s. Refuse, do not shrink.",
        },
        { do: "answer", start_s: null, end_s: null, ok: true, detail: "" },
      ],
      session_id,
      export_url: null,
    }
  }
  if (/audio/.test(q) && /export|clip|wav/.test(q)) {
    const exportId = randomUUID()
    exportsStore.set(`${videoId}:${exportId}`, { filePath: SAMPLE_WAV, type: "audio/wav" })
    return {
      answer: "Wav is ready.",
      citations: [0],
      steps: [
        {
          do: "export_audio",
          start_s: 0,
          end_s: 3,
          ok: true,
          detail: "exported",
        },
        { do: "answer", start_s: null, end_s: null, ok: true, detail: "" },
      ],
      session_id,
      export_url: `/videos/${videoId}/exports/${exportId}`,
    }
  }
  if (/clip|export/.test(q)) {
    const exportId = randomUUID()
    exportsStore.set(`${videoId}:${exportId}`, {
      filePath: row.filePath,
      type: "video/mp4",
    })
    return {
      answer: "Clip is ready.",
      citations: [0, 5],
      steps: [
        {
          do: "export_clip",
          start_s: 0,
          end_s: 5,
          ok: true,
          detail: "exported",
        },
        { do: "answer", start_s: null, end_s: null, ok: true, detail: "" },
      ],
      session_id,
      export_url: `/videos/${videoId}/exports/${exportId}`,
    }
  }
  return {
    answer:
      "Around 12 seconds they mention pricing, then a slide holds. The model looked at a short window instead of the whole file.",
    citations: [12.4, 18],
    steps: [
      { do: "search", start_s: null, end_s: null, ok: true, detail: "pricing" },
      { do: "look", start_s: 12.4, end_s: 16.4, ok: true, detail: "looked" },
      { do: "answer", start_s: null, end_s: null, ok: true, detail: "" },
    ],
    session_id,
    export_url: null,
  }
}

const server = http.createServer(async (req, res) => {
  try {
    if (req.method === "OPTIONS") {
      res.writeHead(204, CORS)
      res.end()
      return
    }
    const url = new URL(req.url || "/", `http://${HOST}:${PORT}`)
    const parts = url.pathname.split("/").filter(Boolean)

    if (req.method === "GET" && url.pathname === "/videos") {
      json(res, 200, [...videos.values()].map((row) => publicVideo(applyIngest(row))))
      return
    }

    if (req.method === "POST" && url.pathname === "/videos") {
      const length = Number(req.headers["content-length"] || 0)
      if (length > MAX_UPLOAD) {
        json(res, 413, { detail: "file too large" })
        return
      }
      const body = await readBody(req)
      const parsed = parseMultipart(body, String(req.headers["content-type"] || ""))
      if (!parsed) {
        json(res, 400, { detail: "expected multipart file" })
        return
      }
      if (parsed.data.length > MAX_UPLOAD) {
        json(res, 413, { detail: "file too large" })
        return
      }
      const id = randomUUID()
      const dest = path.join(DIR, `${id}.mp4`)
      fs.writeFileSync(dest, parsed.data)
      const isAudio = audioName(parsed.filename)
      const row = makeVideo({
        id,
        original_filename: parsed.filename,
        duration_s: probeDuration(dest),
        status: "processing",
        transcript_status: "pending",
        visual_status: "pending",
        audio_status: "pending",
        slides_status: "pending",
        has_video: !isAudio,
        kind: isAudio ? "audio" : "video",
        filePath: dest,
        startedAt: Date.now(),
      })
      videos.set(id, row)
      json(res, 200, publicVideo(applyIngest(row)))
      return
    }

    if (parts[0] === "videos" && parts[1] && parts.length === 2) {
      const row = videos.get(parts[1])
      if (!row) {
        json(res, 404, { detail: "Video not found" })
        return
      }
      if (req.method === "GET") {
        json(res, 200, publicVideo(applyIngest(row)))
        return
      }
      if (req.method === "DELETE") {
        videos.delete(parts[1])
        res.writeHead(204, CORS)
        res.end()
        return
      }
    }

    if (parts[0] === "videos" && parts[2] === "file" && req.method === "GET") {
      const row = videos.get(parts[1])
      if (!row) {
        json(res, 404, { detail: "Video not found" })
        return
      }
      sendFile(req, res, row.filePath, row.has_video === false ? "audio/mpeg" : "video/mp4")
      return
    }

    if (parts[0] === "videos" && parts[2] === "chat" && req.method === "POST") {
      const row = videos.get(parts[1])
      if (!row) {
        json(res, 404, { detail: "Video not found" })
        return
      }
      applyIngest(row)
      if (row.status !== "ready") {
        json(res, 409, { detail: "indexes are still building" })
        return
      }
      const raw = JSON.parse((await readBody(req)).toString("utf8") || "{}")
      await new Promise((resolve) => setTimeout(resolve, 650))
      json(res, 200, chatReply(String(raw.message || ""), row))
      return
    }

    if (parts[0] === "videos" && parts[2] === "exports" && req.method === "GET") {
      const item = exportsStore.get(`${parts[1]}:${parts[3]}`)
      if (!item) {
        json(res, 404, { detail: "Export not found" })
        return
      }
      sendFile(req, res, item.filePath, item.type)
      return
    }

    json(res, 404, { detail: "Not found" })
  } catch (error) {
    json(res, 500, { detail: error instanceof Error ? error.message : "error" })
  }
})

server.listen(PORT, HOST, () => {
  process.stdout.write(`mock API http://${HOST}:${PORT}\n`)
})
