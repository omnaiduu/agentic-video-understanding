const FETCH_TIMEOUT_MS = 10_000

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

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

async function readError(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json()
    if (body && typeof body === "object" && "detail" in body) {
      const detail = (body as { detail: unknown }).detail
      if (typeof detail === "string" && detail.trim()) {
        return detail
      }
    }
  } catch {
    // ignore non-JSON
  }
  return response.statusText || `HTTP ${response.status}`
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

export function listVideos(): Promise<Video[]> {
  return getJson<Video[]>("/videos")
}

export function getVideo(id: string): Promise<Video> {
  return getJson<Video>(`/videos/${id}`)
}

export function isNotFound(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404
}
