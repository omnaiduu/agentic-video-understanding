import { Check, Film, ImageIcon, Mic, PanelsTopLeft, Volume2 } from "lucide-react"

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
  const failed = INDEX_BOOKS.some(
    (book) => indexTone(bookStatus(video, book.key)) === "error",
  )

  if (!building && !failed) {
    return (
      <ul className="flex flex-wrap gap-2">
        {INDEX_BOOKS.map((book) => {
          const raw = bookStatus(video, book.key)
          const tone = indexTone(raw)
          const Icon = BOOK_ICON[book.key]
          return (
            <li
              key={book.key}
              className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-2.5 py-1 text-xs"
            >
              {tone === "ready" ? (
                <Check className="size-3 text-live" />
              ) : (
                <Icon className="size-3 text-muted-foreground" />
              )}
              <span>{book.label}</span>
              {tone === "ready" ? (
                <span className="sr-only">{tone}</span>
              ) : (
                <Badge variant={toneVariant(tone)}>{tone}</Badge>
              )}
            </li>
          )
        })}
      </ul>
    )
  }

  return (
    <Card className="border-border bg-card/80 py-0 shadow-none">
      <CardHeader className="border-b border-border py-3">
        <CardTitle className="flex items-center gap-2 text-sm font-medium">
          {building ? (
            <Spinner className="text-live" />
          ) : (
            <Film className="size-4 text-muted-foreground" />
          )}
          Indexes
        </CardTitle>
      </CardHeader>
      <CardContent className="py-3">
        {building ? (
          <p className="mb-3 text-sm text-muted-foreground">Building indexes…</p>
        ) : null}
        <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {INDEX_BOOKS.map((book) => {
            const raw = bookStatus(video, book.key)
            const tone = indexTone(raw)
            const Icon = BOOK_ICON[book.key]
            return (
              <li
                key={book.key}
                className={cn(
                  "flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border bg-background/60 px-3 py-2.5",
                  tone === "building" && "border-live/40",
                  tone === "error" && "border-destructive/40",
                )}
              >
                <span className="flex items-center gap-2 text-sm">
                  <span
                    className={cn(
                      "grid size-7 place-items-center rounded-lg bg-muted text-muted-foreground",
                      tone === "building" && "index-live text-live",
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
