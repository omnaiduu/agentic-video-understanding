import { useRef } from "react"
import { AudioLines } from "lucide-react"

import { videoFileUrl } from "@/lib/api"
import { cn } from "@/lib/utils"

function prefersReducedMotion() {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  )
}

export function MediaPoster({
  videoId,
  audioOnly,
  className,
}: {
  videoId: string
  audioOnly?: boolean
  className?: string
}) {
  const videoRef = useRef<HTMLVideoElement>(null)

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

  function snapToStill(node: HTMLVideoElement) {
    const duration = Number.isFinite(node.duration) ? node.duration : 1
    const still = Math.min(0.8, Math.max(0, duration - 0.05))
    try {
      node.currentTime = still
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
        className="h-full w-full object-cover transition-transform duration-500 ease-out motion-safe:group-hover:scale-[1.03]"
        muted
        loop
        playsInline
        preload="metadata"
        src={`${videoFileUrl(videoId)}#t=0.8`}
        onLoadedData={(event) => snapToStill(event.currentTarget)}
      />
    </div>
  )
}
