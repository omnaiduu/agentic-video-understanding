import type { ChatStep } from "@/lib/api"

export type ExportKind = "clip" | "audio"

export function exportKindFromSteps(steps?: ChatStep[]): ExportKind {
  if (!steps) {
    return "clip"
  }
  for (let index = steps.length - 1; index >= 0; index -= 1) {
    const action = steps[index]?.do
    if (action === "export_audio") {
      return "audio"
    }
    if (action === "export_clip") {
      return "clip"
    }
  }
  return "clip"
}

export function exportFilename(kind: ExportKind): string {
  return kind === "audio" ? "audio.wav" : "clip.mp4"
}

export function exportFailureNote(steps?: ChatStep[]): string | null {
  const failed = steps?.find(
    (step) => !step.ok && (step.do === "export_clip" || step.do === "export_audio"),
  )
  if (!failed) {
    return null
  }
  const detail = failed.detail || ""
  if (/cap is 60/i.test(detail) || /60s/i.test(detail)) {
    return "That export is longer than 60 seconds. The API refuses long clips instead of shrinking them."
  }
  return detail.trim()
    ? `Export failed. ${detail.trim()}`
    : "Export failed."
}
