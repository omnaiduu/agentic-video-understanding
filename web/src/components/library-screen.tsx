import { Link } from "@tanstack/react-router"

import { StatusBadge } from "@/components/status-badge"
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import type { Video } from "@/lib/api"
import { formatDuration } from "@/lib/format"

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
    return <p className="text-muted-foreground">Loading library…</p>
  }
  if (isError) {
    return (
      <div className="space-y-2">
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
    <ul className="space-y-3">
      {videos.map((video) => (
        <li key={video.id}>
          <Link
            to="/videos/$videoId"
            params={{ videoId: video.id }}
            className="block rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Card>
              <CardHeader>
                <CardTitle>{video.original_filename}</CardTitle>
                <CardDescription className="flex items-center gap-2">
                  <span>{formatDuration(video.duration_s)}</span>
                  <StatusBadge status={video.status} />
                </CardDescription>
              </CardHeader>
            </Card>
          </Link>
        </li>
      ))}
    </ul>
  )
}
