import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

const TONE: Record<string, { label: string; className: string }> = {
  ready: {
    label: "ready",
    className: "border-border bg-background text-muted-foreground",
  },
  processing: {
    label: "processing",
    className: "border-live/30 bg-live/10 text-live",
  },
  uploaded: {
    label: "uploaded",
    className: "border-border bg-muted text-muted-foreground",
  },
  error: {
    label: "error",
    className: "",
  },
}

export function StatusBadge({ status }: { status: string }) {
  const tone = TONE[status]
  if (status === "error") {
    return <Badge variant="destructive">{status}</Badge>
  }
  return (
    <Badge
      variant="outline"
      className={cn("capitalize", tone?.className)}
    >
      {tone?.label ?? status}
    </Badge>
  )
}
