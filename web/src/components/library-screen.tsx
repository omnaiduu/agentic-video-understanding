import { AudioLines, Clock3, Film } from "lucide-react"
import { Link } from "@tanstack/react-router"

import { MediaPoster } from "@/components/media-poster"
import { StatusBadge } from "@/components/status-badge"
import { Skeleton } from "@/components/ui/skeleton"
import type { Video } from "@/lib/api"
import { formatAddedOn, formatDuration } from "@/lib/format"
import { cn } from "@/lib/utils"

export function LibraryScreen({
  isPending,
  isError,
  error,
  videos,
}: {
  isPending: boolean
  isError: boolean
  error: Error | null
  videos: Video[] | undefined
}) {
  if (isPending) {
    return (
      <div className="space-y-3">
        <p className="text-muted-foreground">Loading library…</p>
        <div className="grid gap-4 sm:grid-cols-2">
          <Skeleton className="aspect-[16/10] w-full" />
          <Skeleton className="aspect-[16/10] w-full" />
        </div>
      </div>
    )
  }
  if (isError) {
    return (
      <div className="space-y-2 rounded-2xl border border-destructive/25 bg-destructive/8 px-4 py-4">
        <p className="font-medium">Could not load videos.</p>
        <p className="text-sm text-muted-foreground">
          {error?.message || "The API is unreachable"}. Start FastAPI on port
          8000 and retry.
        </p>
      </div>
    )
  }
  if (!videos || videos.length === 0) {
    return (
      <p className="text-muted-foreground">
        No videos yet. Choose a file above to upload it through FastAPI.
      </p>
    )
  }
  return (
    <ul className="stagger-in grid gap-4 sm:grid-cols-2">
      {videos.map((video) => {
        const Icon = video.has_video ? Film : AudioLines
        return (
          <li key={video.id}>
            <Link
              to="/videos/$videoId"
              params={{ videoId: video.id }}
              className="block rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <article
                className={cn(
                  "group overflow-hidden rounded-2xl border border-white/8 bg-card/80 ring-1 ring-white/4 transition-all duration-300",
                  "hover:-translate-y-1 hover:border-primary/30 hover:shadow-[0_28px_60px_-32px_oklch(0.84_0.12_88/0.7)]",
                )}
              >
                <div className="relative">
                  <MediaPoster
                    seed={video.id}
                    audioOnly={!video.has_video}
                    className="aspect-video"
                  />
                  <span className="absolute top-3 right-3">
                    <StatusBadge status={video.status} />
                  </span>
                  <span className="absolute bottom-3 left-3 inline-flex items-center gap-1 rounded-full bg-black/55 px-2 py-0.5 font-mono text-[11px] text-white/90 ring-1 ring-white/10 backdrop-blur-sm">
                    <Clock3 className="size-3" />
                    {formatDuration(video.duration_s)}
                  </span>
                </div>
                <div className="flex items-start gap-3 px-3.5 py-3">
                  <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg bg-muted text-muted-foreground">
                    <Icon className="size-4" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium tracking-tight">
                      {video.original_filename}
                    </span>
                    {formatAddedOn(video.created_at) ? (
                      <span className="mt-0.5 block text-xs text-muted-foreground">
                        {formatAddedOn(video.created_at)}
                      </span>
                    ) : null}
                  </span>
                </div>
              </article>
            </Link>
          </li>
        )
      })}
    </ul>
  )
}
