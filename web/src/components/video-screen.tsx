import { useCallback, useRef } from "react"
import { Link } from "@tanstack/react-router"

import { ChatPanel } from "@/components/chat-panel"
import { DeleteVideoButton } from "@/components/delete-video-button"
import { IndexPanel } from "@/components/index-panel"
import { StatusBadge } from "@/components/status-badge"
import { buttonVariants } from "@/components/ui/button"
import { VideoPlayer, type SeekFn } from "@/components/video-player"
import { isNotFound, type Video } from "@/lib/api"
import { formatDuration } from "@/lib/format"
import { chatLocked, ingestInProgress } from "@/lib/indexes"
import { clearSessionId } from "@/lib/session"

export function VideoScreen({
  isPending,
  isError,
  error,
  video,
  onDeleted,
}: {
  isPending: boolean
  isError: boolean
  error: Error | null
  video: Video | undefined
  onDeleted?: () => void
}) {
  const seekRef = useRef<SeekFn>(() => undefined)
  const handlePlayerReady = useCallback((seek: SeekFn) => {
    seekRef.current = seek
  }, [])

  if (isPending) {
    return <p className="text-muted-foreground">Loading video…</p>
  }
  if (isError) {
    const missing = isNotFound(error)
    return (
      <div className="space-y-3">
        <p className="font-medium">
          {missing ? "Video not found." : "Could not load this video."}
        </p>
        <p className="text-sm text-muted-foreground">
          {missing
            ? "It may have been deleted, or the link is wrong."
            : error?.message || "The API is unreachable. Start FastAPI on port 8000 and retry."}
        </p>
        <Link to="/" className={buttonVariants({ variant: "outline" })}>
          Back to library
        </Link>
      </div>
    )
  }
  if (!video) {
    return null
  }
  const locked = chatLocked(video)
  const indexesBuilding = ingestInProgress(video)
  const ingestFailed = video.status === "error" || Boolean(video.error_message)
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold">{video.original_filename}</h1>
          <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <span>{formatDuration(video.duration_s)}</span>
            <StatusBadge status={video.status} />
          </div>
        </div>
        <DeleteVideoButton
          videoId={video.id}
          onDeleted={() => {
            clearSessionId(video.id)
            onDeleted?.()
          }}
        />
      </div>
      {ingestFailed ? (
        <p className="text-sm text-destructive" role="alert">
          {video.status === "error"
            ? `This file could not be processed.${video.error_message ? ` ${video.error_message}` : ""}`
            : video.error_message}
        </p>
      ) : null}
      <IndexPanel video={video} />
      <div
        className="grid grid-cols-1 items-start gap-4 md:grid-cols-2"
        data-slot="watch-layout"
      >
        <VideoPlayer video={video} onReady={handlePlayerReady} />
        <ChatPanel
          videoId={video.id}
          locked={locked}
          indexesBuilding={indexesBuilding}
          onSeek={(seconds) => seekRef.current(seconds)}
        />
      </div>
    </div>
  )
}
