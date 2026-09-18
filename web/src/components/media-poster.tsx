import { AudioLines, Play } from "lucide-react"

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
          background: `linear-gradient(152deg,
            oklch(0.3 0.09 ${hue}) 0%,
            oklch(0.15 0.045 ${hue + 36}) 46%,
            oklch(0.2 0.08 88 / 0.62) 100%)`,
        }}
      />
      <div
        className="absolute -top-8 -left-6 size-40 rounded-full blur-3xl"
        style={{ background: `oklch(0.55 0.12 ${hue} / 0.35)` }}
      />
      <div className="poster-scan absolute inset-0 opacity-45" />
      <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-black/20" />
      <span className="absolute inset-0 grid place-items-center">
        <span className="grid size-12 place-items-center rounded-full bg-black/40 text-primary ring-1 ring-white/20 shadow-[0_12px_30px_-12px_black] backdrop-blur-sm transition-transform duration-300 group-hover:scale-110">
          {audioOnly ? <AudioLines className="size-5" /> : <Play className="size-5 fill-current" />}
        </span>
      </span>
    </div>
  )
}
