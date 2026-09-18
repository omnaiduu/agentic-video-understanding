import { AudioLines } from "lucide-react"

import { videoFileUrl } from "@/lib/api"
import { cn } from "@/lib/utils"

export function MediaPoster({
  videoId,
  audioOnly,
  className,
}: {
  videoId: string
  audioOnly?: boolean
  className?: string
}) {
  if (audioOnly) {
    return (
      <div
        className={cn("grid place-items-center bg-muted text-muted-foreground", className)}
        aria-hidden
      >
        <AudioLines className="size-7" />
      </div>
    )
  }
  return (
    <div className={cn("relative overflow-hidden bg-muted", className)} aria-hidden>
      <video
        className="h-full w-full object-cover"
        muted
        playsInline
        preload="metadata"
        src={`${videoFileUrl(videoId)}#t=0.8`}
        onLoadedData={(event) => {
          try {
            event.currentTarget.currentTime = 0.8
          } catch {
            // ignore
          }
        }}
      />
    </div>
  )
}
