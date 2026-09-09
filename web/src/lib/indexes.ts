import type { Video } from "@/lib/api"

export const INDEX_BOOKS = [
  { key: "transcript_status", label: "Speech index" },
  { key: "visual_status", label: "Picture index" },
  { key: "audio_status", label: "Sound index" },
  { key: "slides_status", label: "Slide index" },
] as const

export type IndexBookKey = (typeof INDEX_BOOKS)[number]["key"]

export type IndexTone = "waiting" | "building" | "ready" | "skipped" | "error"

const TONES: Record<string, IndexTone> = {
  pending: "waiting",
  processing: "building",
  ready: "ready",
  skipped: "skipped",
  error: "error",
}

export function bookStatus(video: Video, key: IndexBookKey): string {
  if (key === "slides_status") {
    return video.slides_status ?? "skipped"
  }
  return video[key]
}

export function indexTone(raw: string): IndexTone {
  return TONES[raw] ?? "waiting"
}

export function ingestInProgress(video: Video): boolean {
  if (video.status === "error") {
    return false
  }
  return INDEX_BOOKS.some((book) => {
    const raw = bookStatus(video, book.key)
    return raw === "pending" || raw === "processing"
  })
}

export function chatLocked(video: Video): boolean {
  return video.status !== "ready" || ingestInProgress(video)
}

export function shouldPollVideo(video: Video | undefined): boolean {
  if (!video) {
    return false
  }
  return ingestInProgress(video)
}
