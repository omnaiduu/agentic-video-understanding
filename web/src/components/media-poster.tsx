import { useRef } from "react"
import { AudioLines, Play } from "lucide-react"

import { videoFileUrl } from "@/lib/api"
import { cn } from "@/lib/utils"

function prefersReducedMotion() {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  )
}

export function posterTime(durationS: number | null | undefined): number {
  if (durationS == null || !Number.isFinite(durationS) || durationS <= 1) {
    return 0.4
  }
  return Math.min(12, Math.max(1, durationS * 0.12))
}

export function MediaPoster({
  videoId,
  audioOnly,
  durationS,
  className,
}: {
  videoId: string
  audioOnly?: boolean
  durationS?: number | null
  className?: string
}) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const still = posterTime(durationS)

  if (audioOnly) {
    return (
      <div
        className={cn(
          "grid place-items-center bg-muted text-muted-foreground",
          className,
        )}
        aria-hidden
      >
        <AudioLines className="size-8" />
      </div>
    )
  }

  function snapToStill(node: HTMLVideoElement) {
    const duration = Number.isFinite(node.duration) ? node.duration : still
    const target = Math.min(still, Math.max(0, duration - 0.05))
    try {
      node.currentTime = target
    } catch {
      // ignore
    }
  }

  function preview(play: boolean) {
    const node = videoRef.current
    if (!node || prefersReducedMotion()) {
      return
    }
    if (play) {
      void node.play().catch(() => undefined)
      return
    }
    node.pause()
    snapToStill(node)
  }

  return (
    <div
      className={cn("relative overflow-hidden bg-muted", className)}
      aria-hidden
      onPointerEnter={() => preview(true)}
      onPointerLeave={() => preview(false)}
    >
      <video
        ref={videoRef}
        className="h-full w-full object-cover brightness-110 contrast-110 transition-transform duration-500 ease-out motion-safe:group-hover:scale-[1.04]"
        muted
        loop
        playsInline
        preload="metadata"
        src={`${videoFileUrl(videoId)}#t=${still}`}
        onLoadedData={(event) => snapToStill(event.currentTarget)}
      />
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-black/20" />
      <span className="pointer-events-none absolute top-1/2 left-1/2 grid size-12 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full bg-primary text-primary-foreground opacity-90 shadow-lg transition-transform duration-200 group-hover:scale-105">
        <Play className="size-5 translate-x-px fill-current" />
      </span>
    </div>
  )
}
