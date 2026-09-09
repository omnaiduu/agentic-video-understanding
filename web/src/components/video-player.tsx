import { useEffect, useRef } from "react"

import type { Video } from "@/lib/api"
import { mediaType, videoFileUrl } from "@/lib/api"

export type SeekFn = (seconds: number) => void

export function VideoPlayer({
  video,
  onReady,
}: {
  video: Video
  onReady?: (seek: SeekFn) => void
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const onReadyRef = useRef(onReady)
  onReadyRef.current = onReady

  const src = videoFileUrl(video.id)
  const type = mediaType(video)
  const audioOnly = !video.has_video

  useEffect(() => {
    const node = containerRef.current
    if (!node) {
      return
    }
    let disposed = false
    let player: { currentTime: (time: number) => void; dispose: () => void } | null =
      null

    void (async () => {
      const videojs = (await import("video.js")).default
      await import("video.js/dist/video-js.css")
      if (disposed || !containerRef.current) {
        return
      }
      containerRef.current.replaceChildren()
      const el = document.createElement("video")
      el.className = "video-js vjs-big-play-centered vjs-fluid"
      el.setAttribute("playsinline", "true")
      containerRef.current.appendChild(el)
      player = videojs(el, {
        controls: true,
        preload: "metadata",
        fluid: true,
        playsinline: true,
        audioOnlyMode: audioOnly,
        sources: [{ src, type }],
      })
      onReadyRef.current?.((seconds) => {
        player?.currentTime(seconds)
      })
    })()

    return () => {
      disposed = true
      onReadyRef.current?.(() => undefined)
      player?.dispose()
      player = null
    }
  }, [src, type, audioOnly])

  return (
    <div
      data-slot="player"
      className="overflow-hidden rounded-xl bg-black [&_.video-js]:mx-auto [&_.video-js]:w-full"
    >
      <div ref={containerRef} />
    </div>
  )
}
