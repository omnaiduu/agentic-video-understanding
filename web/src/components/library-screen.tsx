import { Link } from "@tanstack/react-router"

import { MediaPoster } from "@/components/media-poster"
import { StatusBadge } from "@/components/status-badge"
import { Skeleton } from "@/components/ui/skeleton"
import type { Video } from "@/lib/api"
import { formatAddedOn, formatDuration } from "@/lib/format"

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
      <div className="space-y-4">
        <p className="text-muted-foreground">Loading library…</p>
        <div className="grid grid-cols-1 gap-8 xl:grid-cols-2">
          <Skeleton className="h-[min(36rem,52vh)] w-full rounded-2xl xl:[&:only-child]:col-span-2" />
        </div>
      </div>
    )
  }
  if (isError) {
    return (
      <div className="space-y-2 rounded-2xl border border-destructive/30 bg-destructive/10 px-5 py-5">
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
      <div className="rounded-2xl border border-dashed border-border bg-card/40 px-6 py-16 text-center">
        <p className="text-muted-foreground">
          No videos yet. Choose a file above to upload it through FastAPI.
        </p>
      </div>
    )
  }
  return (
    <ul className="grid grid-cols-1 gap-x-8 gap-y-10 xl:grid-cols-2">
      {videos.map((video) => {
        const added = formatAddedOn(video.created_at)
        return (
          <li key={video.id} className="xl:[&:only-child]:col-span-2">
            <Link
              to="/videos/$videoId"
              params={{ videoId: video.id }}
              className="group block rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <article>
                <div className="relative overflow-hidden rounded-2xl border border-border bg-muted shadow-[0_24px_60px_-28px_oklch(0_0_0/0.9)] transition-[border-color,transform] duration-300 group-hover:border-primary/45">
                  <MediaPoster
                    videoId={video.id}
                    audioOnly={!video.has_video}
                    durationS={video.duration_s}
                    className="h-[min(36rem,52vh)] w-full"
                  />
                  {video.status !== "ready" ? (
                    <span className="absolute top-4 left-4">
                      <StatusBadge status={video.status} />
                    </span>
                  ) : null}
                  <span className="absolute right-4 bottom-4 rounded-md bg-black/80 px-2.5 py-1.5 font-mono text-sm font-medium tabular-nums text-white shadow-sm ring-1 ring-white/20 backdrop-blur-md">
                    {formatDuration(video.duration_s)}
                  </span>
                </div>
                <div className="mt-4 flex min-w-0 items-baseline justify-between gap-3 px-0.5">
                  <p className="truncate text-xl font-medium tracking-tight">
                    {video.original_filename}
                  </p>
                  {added ? (
                    <p className="shrink-0 text-sm text-muted-foreground">{added}</p>
                  ) : null}
                </div>
              </article>
            </Link>
          </li>
        )
      })}
    </ul>
  )
}
