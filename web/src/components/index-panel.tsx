import { Film, ImageIcon, Mic, PanelsTopLeft, Volume2 } from "lucide-react"

import { Spinner } from "@/components/spinner"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { Video } from "@/lib/api"
import {
  INDEX_BOOKS,
  bookStatus,
  indexTone,
  ingestInProgress,
  type IndexBookKey,
  type IndexTone,
} from "@/lib/indexes"
import { cn } from "@/lib/utils"

function toneVariant(tone: IndexTone) {
  if (tone === "error") {
    return "destructive" as const
  }
  if (tone === "ready") {
    return "default" as const
  }
  if (tone === "building") {
    return "outline" as const
  }
  return "secondary" as const
}

const BOOK_ICON: Record<IndexBookKey, typeof Mic> = {
  transcript_status: Mic,
  visual_status: ImageIcon,
  audio_status: Volume2,
  slides_status: PanelsTopLeft,
}

export function IndexPanel({ video }: { video: Video }) {
  const building = ingestInProgress(video)
  return (
    <Card className="border-white/5 bg-card/80 shadow-none ring-1 ring-white/6">
      <CardHeader className="border-b border-white/5 pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-medium tracking-tight">
          {building ? <Spinner className="text-live" /> : <Film className="size-4 text-muted-foreground" />}
          Indexes
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-4">
        {building ? (
          <p className="mb-4 text-sm text-muted-foreground">Building indexes…</p>
        ) : null}
        <ul className="grid gap-2 sm:grid-cols-2">
          {INDEX_BOOKS.map((book) => {
            const raw = bookStatus(video, book.key)
            const tone = indexTone(raw)
            const Icon = BOOK_ICON[book.key]
            return (
              <li
                key={book.key}
                className={cn(
                  "flex flex-wrap items-center justify-between gap-2 rounded-xl border border-white/5 bg-background/40 px-3 py-2.5 transition-colors",
                  tone === "building" && "border-live/30 bg-live/5",
                  tone === "ready" && "border-primary/15",
                  tone === "error" && "border-destructive/30",
                )}
              >
                <span className="flex items-center gap-2 text-sm">
                  <span
                    className={cn(
                      "grid size-7 place-items-center rounded-lg bg-muted text-muted-foreground",
                      tone === "building" && "index-live bg-live/15 text-live",
                      tone === "ready" && "bg-primary/15 text-primary",
                    )}
                  >
                    <Icon className="size-3.5" />
                  </span>
                  {book.label}
                </span>
                <span className="flex items-center gap-2">
                  {tone === "building" ? <Spinner className="text-live" /> : null}
                  <Badge variant={toneVariant(tone)}>{tone}</Badge>
                </span>
                {tone === "error" && video.error_message ? (
                  <p className="w-full text-sm text-destructive">
                    {video.error_message}
                  </p>
                ) : null}
              </li>
            )
          })}
        </ul>
      </CardContent>
    </Card>
  )
}
