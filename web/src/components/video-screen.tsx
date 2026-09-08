import { Link } from "@tanstack/react-router"

import { StatusBadge } from "@/components/status-badge"
import { buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { isNotFound, type Video } from "@/lib/api"
import { formatDuration } from "@/lib/format"

export function VideoScreen({
  isPending,
  isError,
  error,
  video,
}: {
  isPending: boolean
  isError: boolean
  error: Error | null
  video: Video | undefined
}) {
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
            : error?.message || "The API is down."}
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
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold">{video.original_filename}</h1>
        <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <span>{formatDuration(video.duration_s)}</span>
          <StatusBadge status={video.status} />
        </div>
        {video.error_message ? (
          <p className="text-sm text-destructive">{video.error_message}</p>
        ) : null}
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Player (Phase 11)</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          The source file will play here later. No player in this phase.
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Chat (Phase 11)</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Ask questions here later. This shell does not POST chat and never
          talks to Gemma from the browser.
        </CardContent>
      </Card>
    </div>
  )
}
