import { Badge } from "@/components/ui/badge"

export function StatusBadge({ status }: { status: string }) {
  const variant =
    status === "error"
      ? "destructive"
      : status === "ready"
        ? "default"
        : "secondary"
  return <Badge variant={variant}>{status}</Badge>
}
