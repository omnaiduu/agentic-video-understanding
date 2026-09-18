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
const SAMPLE_MP4 = path.join(DIR, "sample.mp4")
const SAMPLE_WAV = path.join(DIR, "sample.wav")
const MAX_UPLOAD = 2 * 1024 * 1024 * 1024
const BOOKS = ["transcript_status", "visual_status", "audio_status", "slides_status"]

fs.mkdirSync(DIR, { recursive: true })

function ensureMedia() {
  if (!fs.existsSync(SAMPLE_MP4)) {
    const made = spawnSync(
      "ffmpeg",
      [
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=1280x720:rate=30",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:sample_rate=44100",
        "-t",
        "8",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        SAMPLE_MP4,
      ],
      { stdio: "ignore" },
    )
    if (made.status !== 0) {
      throw new Error("ffmpeg could not create the demo mp4")
    }
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
    kind: "video",
    duration_s: partial.duration_s ?? 8,
    fps: 30,
    has_audio: true,
    has_video: true,
    status: partial.status || "ready",
    transcript_status: partial.transcript_status || "ready",
    visual_status: partial.visual_status || "ready",
    audio_status: partial.audio_status || "ready",
    slides_status: partial.slides_status || "ready",
    error_message: null,
    created_at: partial.created_at || new Date().toISOString(),
    filePath: partial.filePath || SAMPLE_MP4,
    startedAt: partial.startedAt || Date.now(),
  }
}

const videos = new Map()
const exportsStore = new Map()

videos.set(
  "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  makeVideo({
    id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    original_filename: "GTC keynote — pricing.mp4",
    duration_s: 125,
    created_at: "2026-04-08T12:00:00Z",
  }),
)
videos.set(
  "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
  makeVideo({
    id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    original_filename: "Warehouse cam 12.mp4",
    duration_s: 48,
    status: "processing",
    transcript_status: "ready",
    visual_status: "processing",
    audio_status: "pending",
    slides_status: "pending",
    created_at: new Date().toISOString(),
    startedAt: Date.now() - 1300,
  }),
)

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
    let dataEnd = next - 2
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

function chatReply(message, videoId) {
  const q = message.toLowerCase()
  const session_id = randomUUID()
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
    exportsStore.set(`${videoId}:${exportId}`, { filePath: SAMPLE_MP4, type: "video/mp4" })
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
      const dest = path.join(DIR, `${id}.bin`)
      fs.writeFileSync(dest, parsed.data)
      const row = makeVideo({
        id,
        original_filename: parsed.filename,
        duration_s: 8,
        status: "processing",
        transcript_status: "pending",
        visual_status: "pending",
        audio_status: "pending",
        slides_status: "pending",
        filePath: SAMPLE_MP4,
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
      sendFile(req, res, row.filePath, "video/mp4")
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
      json(res, 200, chatReply(String(raw.message || ""), parts[1]))
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
