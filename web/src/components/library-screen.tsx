import { AudioLines, Clock3, Film } from "lucide-react"
import { Link } from "@tanstack/react-router"

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
        <div className="space-y-3">
          <Skeleton className="h-[4.5rem] w-full" />
          <Skeleton className="h-[4.5rem] w-full" />
          <Skeleton className="h-[4.5rem] w-full" />
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
    <ul className="stagger-in space-y-3">
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
                  "group flex items-center gap-4 rounded-2xl border border-white/6 bg-card/80 px-4 py-3.5 ring-1 ring-white/4 transition-all duration-200",
                  "hover:-translate-y-0.5 hover:border-primary/25 hover:bg-card hover:shadow-[0_20px_40px_-28px_oklch(0.84_0.12_88/0.55)]",
                )}
              >
                <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-muted text-muted-foreground transition-colors group-hover:bg-primary/15 group-hover:text-primary">
                  <Icon className="size-5" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium tracking-tight">
                    {video.original_filename}
                  </span>
                  <span className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <span className="inline-flex items-center gap-1">
                      <Clock3 className="size-3" />
                      {formatDuration(video.duration_s)}
                    </span>
                    {formatAddedOn(video.created_at) ? (
                      <span>{formatAddedOn(video.created_at)}</span>
                    ) : null}
                    <StatusBadge status={video.status} />
                  </span>
                </span>
                <span className="hidden text-xs text-muted-foreground transition-colors group-hover:text-foreground sm:inline">
                  Open
                </span>
              </article>
            </Link>
          </li>
        )
      })}
    </ul>
  )
}
