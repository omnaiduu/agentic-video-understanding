const FETCH_TIMEOUT_MS = 10_000
const CHAT_TIMEOUT_MS = 180_000

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

export function getApiBaseUrl(): string {
  const vite = import.meta.env.VITE_API_URL as string | undefined
  const node =
    typeof process !== "undefined"
      ? process.env.VITE_API_URL || process.env.API_URL
      : undefined
  const raw = (vite || node || "http://127.0.0.1:8000").trim()
  return raw.replace(/\/$/, "")
}

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
      headers: { "Content-Type": "application/json" },
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

export type ChatOut = {
  answer: string
  citations: number[]
  steps: ChatStep[]
  session_id: string
  export_url: string | null
}

export function postChat(
  videoId: string,
  message: string,
  sessionId?: string | null,
): Promise<ChatOut> {
  const body: { message: string; session_id?: string } = { message }
  if (sessionId) {
    body.session_id = sessionId
  }
  return postJson<ChatOut>(`/videos/${videoId}/chat`, body, CHAT_TIMEOUT_MS)
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
