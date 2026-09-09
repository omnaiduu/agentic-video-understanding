import { ApiError } from "@/lib/api"

export function humanizeChatError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 503) {
      return "The language model is not available. Start Gemma or a FakeBrain and try again."
    }
    if (error.status === 0) {
      if (/timed out/i.test(error.message)) {
        return "The API timed out."
      }
      return "The API is unreachable. Start FastAPI on port 8000 and retry."
    }
    const detail = error.message.trim()
    if (/cap is 60/i.test(detail) || /requested .+s export/i.test(detail)) {
      return "That export is longer than 60 seconds. The API refuses long clips instead of shrinking them."
    }
    return detail || "Chat failed."
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message
  }
  return "Chat failed."
}
