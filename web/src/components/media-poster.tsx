import { AudioLines, Film, Play } from "lucide-react"

import { posterHue } from "@/lib/poster"
import { cn } from "@/lib/utils"

export function MediaPoster({
  seed,
  audioOnly,
  className,
}: {
  seed: string
  audioOnly?: boolean
  className?: string
}) {
  const hue = posterHue(seed)
  return (
    <div
      className={cn("card-shine relative overflow-hidden bg-black", className)}
      aria-hidden
    >
      <div
        className="absolute inset-0"
        style={{
          background: `linear-gradient(145deg,
            oklch(0.28 0.08 ${hue}) 0%,
            oklch(0.16 0.04 ${hue + 40}) 48%,
            oklch(0.22 0.1 88 / 0.55) 100%)`,
        }}
      />
      <div className="poster-scan absolute inset-0 opacity-40" />
      <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-transparent" />
      <span className="absolute inset-0 grid place-items-center">
        <span className="grid size-11 place-items-center rounded-full bg-black/35 text-primary ring-1 ring-white/15 backdrop-blur-sm transition-transform duration-300 group-hover:scale-110">
          {audioOnly ? <AudioLines className="size-5" /> : <Play className="size-5 fill-current" />}
        </span>
      </span>
      <Film className="absolute top-3 left-3 size-4 text-white/35" />
    </div>
  )
}
