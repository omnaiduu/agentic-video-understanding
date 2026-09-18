import { useCallback, useLayoutEffect, useState } from "react"
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
import { chatLocked } from "@/lib/indexes"
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
  const [seek, setSeek] = useState<SeekFn>(() => () => undefined)
  const [playerEl, setPlayerEl] = useState<HTMLDivElement | null>(null)
  const [chatHeight, setChatHeight] = useState<number | null>(null)
  const handlePlayerReady = useCallback((next: SeekFn) => {
    setSeek(() => next)
  }, [])

  useLayoutEffect(() => {
    if (!playerEl) {
      return
    }
    const sync = () => {
      const desktop = window.matchMedia?.("(min-width: 768px)").matches ?? false
      setChatHeight(desktop ? Math.round(playerEl.getBoundingClientRect().height) : null)
    }
    sync()
    const observer =
      typeof ResizeObserver === "undefined" ? null : new ResizeObserver(sync)
    observer?.observe(playerEl)
    window.addEventListener("resize", sync)
    const media = window.matchMedia?.("(min-width: 768px)")
    media?.addEventListener("change", sync)
    return () => {
      observer?.disconnect()
      window.removeEventListener("resize", sync)
      media?.removeEventListener("change", sync)
    }
  }, [playerEl])

  if (isPending) {
    return (
      <div className="space-y-4">
        <p className="text-muted-foreground">Loading video…</p>
        <Skeleton className="h-8 w-2/3" />
        <div className="overflow-hidden rounded-3xl border border-white/8">
          <Skeleton className="aspect-video w-full rounded-none" />
        </div>
      </div>
    )
  }
  if (isError) {
    const missing = isNotFound(error)
    return (
      <div className="app-enter space-y-3 rounded-2xl border border-destructive/25 bg-destructive/8 px-4 py-5">
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
  const ingestFailed = video.status === "error" || Boolean(video.error_message)

  return (
    <div data-page="watch" className="app-enter flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1.5">
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-xs font-medium tracking-wide text-muted-foreground uppercase transition-colors hover:text-foreground"
          >
            <ArrowLeft className="size-3.5" />
            Library
          </Link>
          <span className="hidden h-4 w-px bg-white/10 sm:block" />
          <h1 className="max-w-[min(100%,36rem)] truncate font-serif text-xl font-medium tracking-tight sm:text-2xl">
            {video.original_filename}
          </h1>
          <span className="font-mono text-xs text-muted-foreground">
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
      <div className="studio-bay overflow-hidden rounded-3xl bg-card/80">
        <div
          className="grid grid-cols-1 items-start md:grid-cols-2"
          data-slot="watch-layout"
        >
          <div
            ref={setPlayerEl}
            className="w-full border-white/8 max-md:border-b md:border-r"
          >
            <VideoPlayer video={video} onReady={handlePlayerReady} />
          </div>
          <div
            className="min-h-[22rem] md:min-h-0"
            style={chatHeight ? { height: chatHeight } : undefined}
          >
            <ChatPanel
              videoId={video.id}
              locked={locked}
              onSeek={(seconds) => seek(seconds)}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
