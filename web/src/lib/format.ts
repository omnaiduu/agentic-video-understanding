export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || !Number.isFinite(seconds)) {
    return "—"
  }
  if (seconds < 60) {
    const rounded = Math.round(seconds * 10) / 10
    const label = Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1)
    return `${label}s`
  }
  const minutes = Math.floor(seconds / 60)
  const rest = Math.round(seconds % 60)
  return `${minutes}m ${rest}s`
}
