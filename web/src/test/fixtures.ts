import type { Video } from "@/lib/api"

export function sampleVideo(overrides: Partial<Video> = {}): Video {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    original_filename: "demo.mp4",
    path: "/data/videos/11111111-1111-1111-1111-111111111111/original.mp4",
    kind: "video",
    duration_s: 42,
    fps: 30,
    has_audio: true,
    has_video: true,
    status: "ready",
    transcript_status: "ready",
    visual_status: "ready",
    audio_status: "ready",
    error_message: null,
    created_at: "2026-04-08T12:00:00Z",
    ...overrides,
  }
}
