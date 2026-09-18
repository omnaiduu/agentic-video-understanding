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
      <div className="space-y-3">
        <p className="text-muted-foreground">Loading library…</p>
        <div className="grid gap-x-4 gap-y-6 sm:grid-cols-2 lg:grid-cols-3">
          <Skeleton className="aspect-video w-full rounded-lg" />
          <Skeleton className="aspect-video w-full rounded-lg" />
        </div>
      </div>
    )
  }
  if (isError) {
    return (
      <div className="space-y-2 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-4">
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
    <ul className="grid gap-x-4 gap-y-6 sm:grid-cols-2 lg:grid-cols-3">
      {videos.map((video) => {
        const added = formatAddedOn(video.created_at)
        return (
          <li key={video.id}>
            <Link
              to="/videos/$videoId"
              params={{ videoId: video.id }}
              className="group block rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <article>
                <div className="relative overflow-hidden rounded-lg border border-border bg-muted">
                  <MediaPoster
                    videoId={video.id}
                    audioOnly={!video.has_video}
                    className="aspect-video"
                  />
                  <span className="absolute top-2 right-2">
                    <StatusBadge status={video.status} />
                  </span>
                  <span className="absolute right-2 bottom-2 rounded bg-black/70 px-1.5 py-0.5 font-mono text-[11px] text-white">
                    {formatDuration(video.duration_s)}
                  </span>
                </div>
                <div className="mt-2 min-w-0">
                  <p className="truncate text-sm font-medium group-hover:underline">
                    {video.original_filename}
                  </p>
                  {added ? (
                    <p className="mt-0.5 text-xs text-muted-foreground">{added}</p>
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
