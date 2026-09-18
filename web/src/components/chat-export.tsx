import { Download } from "lucide-react"

import { buttonVariants } from "@/components/ui/button"
import { absoluteApiUrl } from "@/lib/api"
import {
  exportFilename,
  type ExportKind,
} from "@/lib/export"

export function ChatExport({
  path,
  kind,
}: {
  path: string
  kind: ExportKind
}) {
  const href = absoluteApiUrl(path)
  const filename = exportFilename(kind)
  return (
    <div className="space-y-2 overflow-hidden rounded-md border border-border bg-muted p-2">
      {kind === "audio" ? (
        <audio
          aria-label="Exported audio"
          className="w-full"
          controls
          preload="metadata"
          src={href}
        />
      ) : (
        <video
          aria-label="Exported clip"
          className="max-h-48 w-full rounded-lg bg-black"
          controls
          playsInline
          preload="metadata"
          src={href}
        />
      )}
      <a
        className={buttonVariants({ variant: "outline", size: "sm" })}
        download={filename}
        href={href}
      >
        <Download data-icon="inline-start" />
        Download
      </a>
    </div>
  )
}
