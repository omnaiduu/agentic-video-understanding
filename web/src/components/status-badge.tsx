import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

const TONE: Record<string, string> = {
  ready: "border-live/25 bg-live/10 text-live",
  processing: "border-primary/30 bg-primary/10 text-primary",
  uploaded: "border-border bg-muted text-muted-foreground",
  error: "",
}

export function StatusBadge({ status }: { status: string }) {
  if (status === "error") {
    return <Badge variant="destructive">{status}</Badge>
  }
  return (
    <Badge variant="outline" className={cn("capitalize", TONE[status])}>
      {status}
    </Badge>
  )
}
