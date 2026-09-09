import { Spinner } from "@/components/spinner"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { Video } from "@/lib/api"
import {
  INDEX_BOOKS,
  bookStatus,
  indexTone,
  ingestInProgress,
} from "@/lib/indexes"

function toneVariant(tone: ReturnType<typeof indexTone>) {
  if (tone === "error") {
    return "destructive" as const
  }
  if (tone === "ready") {
    return "default" as const
  }
  return "secondary" as const
}

export function IndexPanel({ video }: { video: Video }) {
  const building = ingestInProgress(video)
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {building ? <Spinner /> : null}
          Indexes
        </CardTitle>
      </CardHeader>
      <CardContent>
        {building ? (
          <p className="mb-3 text-sm text-muted-foreground">Building indexes…</p>
        ) : null}
        <ul className="space-y-2">
          {INDEX_BOOKS.map((book) => {
            const raw = bookStatus(video, book.key)
            const tone = indexTone(raw)
            return (
              <li
                key={book.key}
                className="flex flex-wrap items-center justify-between gap-2"
              >
                <span className="text-sm">{book.label}</span>
                <span className="flex items-center gap-2">
                  {tone === "building" ? <Spinner /> : null}
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
