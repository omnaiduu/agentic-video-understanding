import { useCallback, useRef } from "react"
import { ArrowLeft } from "lucide-react"
import { Link } from "@tanstack/react-router"

import { ChatPanel } from "@/components/chat-panel"
import { DeleteVideoButton } from "@/components/delete-video-button"
import { IndexPanel } from "@/components/index-panel"
import { StatusBadge } from "@/components/status-badge"
import { buttonVariants } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
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
    return (
      <div className="space-y-4">
        <p className="text-muted-foreground">Loading video…</p>
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="aspect-video w-full rounded-2xl" />
      </div>
    )
  }
  if (isError) {
    const missing = isNotFound(error)
    return (
      <div className="app-enter space-y-3 rounded-2xl border border-destructive/30 bg-destructive/10 px-5 py-6">
        <p className="font-medium">
          {missing ? "Video not found." : "Could not load this video."}
        </p>
        <p className="text-sm text-muted-foreground">
          {missing
            ? "It may have been deleted, or the link is wrong."
            : error?.message || "The API is unreachable. Start FastAPI on port 8000 and retry."}
        </p>
        <Link to="/" className={buttonVariants({ variant: "outline", size: "lg" })}>
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
    <div data-page="watch" className="app-enter flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2">
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-base text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="size-4" />
            Library
          </Link>
          <span className="hidden h-5 w-px bg-border sm:block" />
          <h1 className="max-w-[min(100%,42rem)] truncate text-2xl font-semibold tracking-tight sm:text-3xl">
            {video.original_filename}
          </h1>
          <span className="font-mono text-sm tabular-nums text-muted-foreground">
            {formatDuration(video.duration_s)}
          </span>
          <StatusBadge status={video.status} />
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
        className="grid grid-cols-1 items-start overflow-hidden rounded-2xl border border-border bg-card shadow-[0_30px_80px_-40px_oklch(0_0_0/0.85)] md:grid-cols-2 md:items-stretch"
        data-slot="watch-layout"
      >
        <div className="min-w-0 border-border max-md:border-b md:border-r">
          <VideoPlayer video={video} onReady={handlePlayerReady} />
        </div>
        <div className="flex min-h-[22rem] min-w-0 flex-col md:min-h-0">
          <ChatPanel
            videoId={video.id}
            locked={locked}
            indexesBuilding={indexesBuilding}
            onSeek={(seconds) => seekRef.current(seconds)}
          />
        </div>
      </div>
    </div>
  )
}
