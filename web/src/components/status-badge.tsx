import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

const TONE: Record<string, { label: string; className: string }> = {
  ready: {
    label: "ready",
    className: "border-primary/20 bg-primary/12 text-primary",
  },
  processing: {
    label: "processing",
    className: "border-live/25 bg-live/12 text-live",
  },
  uploaded: {
    label: "uploaded",
    className: "border-white/10 bg-muted text-muted-foreground",
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
