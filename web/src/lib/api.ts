const FETCH_TIMEOUT_MS = 10_000
const CHAT_TIMEOUT_MS = 180_000
const THINKING_CHAT_TIMEOUT_MS = 600_000

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

export const DEFAULT_MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024
const UPLOAD_FIELD = "file"

export type Video = {
  id: string
  original_filename: string
  path: string
  kind: string
  duration_s: number | null
  fps: number | null
  has_audio: boolean
  has_video: boolean
  status: string
  transcript_status: string
  visual_status: string
  audio_status: string
  slides_status?: string | null
  error_message: string | null
  created_at: string
}

export const videoKeys = {
  all: ["videos"] as const,
  detail: (id: string) => ["videos", id] as const,
}

function readExplicitApiUrl(): string {
  const vite = (import.meta.env.VITE_API_URL as string | undefined) ?? ""
  const node =
    typeof process !== "undefined"
      ? process.env.VITE_API_URL || process.env.API_URL || ""
      : ""
  return (vite || node).trim()
}

function isLoopbackApiUrl(raw: string): boolean {
  if (!raw || raw === "/" || raw === "same-origin") {
    return true
  }
  try {
    const url = new URL(raw)
    return url.hostname === "localhost" || url.hostname === "127.0.0.1"
  } catch {
    return false
  }
}

export function getApiBaseUrl(): string {
  const explicit = readExplicitApiUrl()
  if (typeof window !== "undefined") {
    if (explicit && !isLoopbackApiUrl(explicit)) {
      return explicit.replace(/\/$/, "")
    }
    return window.location.origin
  }
  if (!explicit || isLoopbackApiUrl(explicit)) {
    return "http://127.0.0.1:8000"
  }
  return explicit.replace(/\/$/, "")
}

const JSON_ACCEPT = { Accept: "application/json" }

function detailFromBody(text: string, fallback: string): string {
  try {
    const body: unknown = JSON.parse(text)
    if (body && typeof body === "object" && "detail" in body) {
      const detail = (body as { detail: unknown }).detail
      if (typeof detail === "string" && detail.trim()) {
        return detail
      }
    }
  } catch {
    // ignore non-JSON
  }
  return fallback
}

async function readError(response: Response): Promise<string> {
  try {
    return detailFromBody(await response.text(), response.statusText || `HTTP ${response.status}`)
  } catch {
    return response.statusText || `HTTP ${response.status}`
  }
}

async function getJson<T>(path: string): Promise<T> {
  const url = `${getApiBaseUrl()}${path}`
  let response: Response
  try {
    response = await fetch(url, {
      headers: JSON_ACCEPT,
      signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === "TimeoutError") {
      throw new ApiError(0, "The API timed out")
    }
    throw new ApiError(0, "The API is unreachable")
  }
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response))
  }
  return (await response.json()) as T
}

async function postJson<T>(
  path: string,
  body: unknown,
  timeoutMs: number,
): Promise<T> {
  const url = `${getApiBaseUrl()}${path}`
  let response: Response
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { ...JSON_ACCEPT, "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(timeoutMs),
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === "TimeoutError") {
      throw new ApiError(0, "The API timed out")
    }
    throw new ApiError(0, "The API is unreachable")
  }
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response))
  }
  return (await response.json()) as T
}

export function listVideos(): Promise<Video[]> {
  return getJson<Video[]>("/videos")
}

export function getVideo(id: string): Promise<Video> {
  return getJson<Video>(`/videos/${id}`)
}

export function videoFileUrl(id: string): string {
  return `${getApiBaseUrl()}/videos/${id}/file`
}

export function mediaType(video: Pick<Video, "has_video" | "kind" | "original_filename">): string {
  if (video.has_video || video.kind === "video") {
    return "video/mp4"
  }
  const name = video.original_filename.toLowerCase()
  if (name.endsWith(".wav")) {
    return "audio/wav"
  }
  if (name.endsWith(".mp3")) {
    return "audio/mpeg"
  }
  if (name.endsWith(".m4a") || name.endsWith(".aac")) {
    return "audio/mp4"
  }
  if (name.endsWith(".ogg") || name.endsWith(".opus")) {
    return "audio/ogg"
  }
  if (name.endsWith(".flac")) {
    return "audio/flac"
  }
  return "audio/mpeg"
}

export type ChatStep = {
  do: string
  start_s: number | null
  end_s: number | null
  ok: boolean
  detail: string
}

export type ChatThought = {
  do: string
  text: string
}

export type ChatOut = {
  answer: string
  citations: number[]
  steps: ChatStep[]
  session_id: string
  export_url: string | null
  thinking?: boolean
  thoughts?: ChatThought[]
}

type ChatStreamLine = {
  event?: string
  status?: string | number
  detail?: string
  session_id?: string
  answer?: string
  citations?: number[]
  steps?: ChatStep[]
  export_url?: string | null
  thinking?: boolean
  thoughts?: ChatThought[]
}

function parseChatStream(text: string): {
  done: ChatOut | null
  error: { status: number; detail: string } | null
  sessionId: string | null
} {
  let done: ChatOut | null = null
  let error: { status: number; detail: string } | null = null
  let sessionId: string | null = null
  for (const line of text.split("\n")) {
    const trimmed = line.trim()
    if (!trimmed.startsWith("{")) {
      continue
    }
    let row: ChatStreamLine
    try {
      row = JSON.parse(trimmed) as ChatStreamLine
    } catch {
      continue
    }
    if (typeof row.session_id === "string" && row.session_id) {
      sessionId = row.session_id
    }
    if (row.event === "error") {
      error = {
        status: typeof row.status === "number" ? row.status : 503,
        detail: row.detail || "Chat failed.",
      }
    }
    if (row.event === "done" && typeof row.answer === "string" && row.session_id) {
      done = {
        answer: row.answer,
        citations: row.citations ?? [],
        steps: row.steps ?? [],
        session_id: row.session_id,
        export_url: row.export_url ?? null,
        thinking: row.thinking,
        thoughts: row.thoughts,
      }
    }
  }
  return { done, error, sessionId }
}

async function readChatStream(
  response: Response,
  onSession: (sessionId: string) => void,
): Promise<ChatOut> {
  const reader = response.body?.getReader()
  if (!reader) {
    const parsed = parseChatStream(await response.text())
    if (parsed.sessionId) {
      onSession(parsed.sessionId)
    }
    if (parsed.error && !parsed.done) {
      throw new ApiError(parsed.error.status, parsed.error.detail)
    }
    if (!parsed.done) {
      throw new ApiError(0, "The API is unreachable")
    }
    return parsed.done
  }
  const decoder = new TextDecoder()
  let buf = ""
  while (true) {
    const chunk = await reader.read()
    if (chunk.done) {
      break
    }
    buf += decoder.decode(chunk.value, { stream: true })
    const parsed = parseChatStream(buf)
    if (parsed.sessionId) {
      onSession(parsed.sessionId)
    }
    if (parsed.done) {
      return parsed.done
    }
    if (parsed.error) {
      throw new ApiError(parsed.error.status, parsed.error.detail)
    }
  }
  const parsed = parseChatStream(buf)
  if (parsed.sessionId) {
    onSession(parsed.sessionId)
  }
  if (parsed.error && !parsed.done) {
    throw new ApiError(parsed.error.status, parsed.error.detail)
  }
  if (!parsed.done) {
    throw new ApiError(0, "The API is unreachable")
  }
  return parsed.done
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}

async function pollChatResult(
  videoId: string,
  sessionId: string,
  message: string,
  timeoutMs: number,
): Promise<ChatOut | null> {
  const deadline = Date.now() + timeoutMs
  const path = `/videos/${videoId}/chat/${sessionId}/result?message=${encodeURIComponent(message)}`
  while (Date.now() < deadline) {
    await sleep(2000)
    try {
      const row = await getJson<ChatStreamLine>(path)
      if (row.status === "done" && typeof row.answer === "string" && row.session_id) {
        return {
          answer: row.answer,
          citations: row.citations ?? [],
          steps: row.steps ?? [],
          session_id: row.session_id,
          export_url: row.export_url ?? null,
          thinking: row.thinking,
          thoughts: row.thoughts,
        }
      }
    } catch {
      // A dropped poll is not the end of the turn. The next one can still land.
    }
  }
  return null
}

export function postChat(
  videoId: string,
  message: string,
  sessionId?: string | null,
  thinking = false,
): Promise<ChatOut> {
  const body: { message: string; session_id?: string; thinking?: boolean } = {
    message,
  }
  if (sessionId) {
    body.session_id = sessionId
  }
  if (thinking) {
    body.thinking = true
  }
  const timeout = thinking ? THINKING_CHAT_TIMEOUT_MS : CHAT_TIMEOUT_MS
  return postChatStream(videoId, message, body, sessionId ?? null, timeout)
}

async function postChatStream(
  videoId: string,
  message: string,
  body: { message: string; session_id?: string; thinking?: boolean },
  sessionId: string | null,
  timeoutMs: number,
): Promise<ChatOut> {
  const url = `${getApiBaseUrl()}/videos/${videoId}/chat/stream`
  let knownSession = sessionId
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { ...JSON_ACCEPT, "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(timeoutMs),
    })
    if (!response.ok) {
      throw new ApiError(response.status, await readError(response))
    }
    return await readChatStream(response, (id) => {
      knownSession = id
    })
  } catch (error) {
    const dropped = !(error instanceof ApiError) || error.status === 0
    if (dropped && knownSession) {
      const recovered = await pollChatResult(videoId, knownSession, message, timeoutMs)
      if (recovered) {
        return recovered
      }
    }
    if (error instanceof DOMException && error.name === "TimeoutError") {
      throw new ApiError(0, "The API timed out")
    }
    if (error instanceof ApiError) {
      throw error
    }
    throw new ApiError(0, "The API is unreachable")
  }
}

export function absoluteApiUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) {
    return path
  }
  const prefix = path.startsWith("/") ? path : `/${path}`
  return `${getApiBaseUrl()}${prefix}`
}

export function deleteVideo(id: string): Promise<void> {
  return sendNoContent("DELETE", `/videos/${id}`)
}

async function sendNoContent(method: string, path: string): Promise<void> {
  const url = `${getApiBaseUrl()}${path}`
  let response: Response
  try {
    response = await fetch(url, {
      method,
      headers: JSON_ACCEPT,
      signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === "TimeoutError") {
      throw new ApiError(0, "The API timed out")
    }
    throw new ApiError(0, "The API is unreachable")
  }
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response))
  }
}

export function isNotFound(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404
}

export function isOversize(error: unknown): boolean {
  return error instanceof ApiError && error.status === 413
}

export function oversizeMessage(error?: unknown): string {
  if (error instanceof ApiError && error.message.trim()) {
    const detail = error.message.trim()
    if (detail.toLowerCase() === "file too large") {
      return "File is too large (2 GB max)."
    }
    return detail
  }
  return "File is too large (2 GB max)."
}

export function uploadVideo(
  file: File,
  onProgress?: (percent: number) => void,
): Promise<Video> {
  if (file.size > DEFAULT_MAX_UPLOAD_BYTES) {
    return Promise.reject(new ApiError(413, "file too large"))
  }
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open("POST", `${getApiBaseUrl()}/videos`)
    xhr.setRequestHeader("Accept", "application/json")
    xhr.upload.onprogress = (event) => {
      if (!onProgress || !event.lengthComputable || event.total === 0) {
        return
      }
      onProgress(Math.min(100, Math.round((event.loaded / event.total) * 100)))
    }
    xhr.onload = () => {
      const fallback = xhr.statusText || `HTTP ${xhr.status}`
      const message = detailFromBody(xhr.responseText || "", fallback)
      if (xhr.status < 200 || xhr.status >= 300) {
        reject(new ApiError(xhr.status, message))
        return
      }
      try {
        resolve(JSON.parse(xhr.responseText) as Video)
      } catch {
        reject(new ApiError(xhr.status, "The API returned an invalid response"))
      }
    }
    xhr.onerror = () => {
      reject(new ApiError(0, "The API is unreachable"))
    }
    xhr.ontimeout = () => {
      reject(new ApiError(0, "The API timed out"))
    }
    const body = new FormData()
    body.append(UPLOAD_FIELD, file)
    xhr.send(body)
  })
}
