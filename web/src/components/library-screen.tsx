import { Clock3 } from "lucide-react"
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
          <Skeleton className="aspect-video w-full rounded-2xl" />
          <Skeleton className="aspect-video w-full rounded-2xl" />
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
      <div className="rounded-3xl border border-dashed border-white/10 bg-card/30 px-5 py-10 text-center">
        <p className="text-muted-foreground">
          No videos yet. Choose a file above to upload it through FastAPI.
        </p>
      </div>
    )
  }
  return (
    <ul className="stagger-in grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {videos.map((video) => {
        const added = formatAddedOn(video.created_at)
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
                  "hover:-translate-y-1 hover:border-primary/35 hover:shadow-[0_28px_60px_-32px_oklch(0.84_0.12_88/0.7)]",
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
                  <div className="absolute inset-x-0 bottom-0 space-y-1.5 bg-gradient-to-t from-black/85 via-black/45 to-transparent px-3.5 pt-12 pb-3">
                    <span className="block truncate text-sm font-medium tracking-tight text-white">
                      {video.original_filename}
                    </span>
                    <span className="flex flex-wrap items-center gap-2 text-[11px] text-white/75">
                      <span className="inline-flex items-center gap-1 font-mono">
                        <Clock3 className="size-3" />
                        {formatDuration(video.duration_s)}
                      </span>
                      {added ? <span>{added}</span> : null}
                    </span>
                  </div>
                </div>
              </article>
            </Link>
          </li>
        )
      })}
    </ul>
  )
}
