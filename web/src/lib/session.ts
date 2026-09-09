const PREFIX = "agentic-video.session."

export function sessionStorageKey(videoId: string): string {
  return `${PREFIX}${videoId}`
}

export function loadSessionId(videoId: string): string | null {
  if (typeof window === "undefined") {
    return null
  }
  return window.localStorage.getItem(sessionStorageKey(videoId))
}

export function saveSessionId(videoId: string, sessionId: string): void {
  if (typeof window === "undefined") {
    return
  }
  window.localStorage.setItem(sessionStorageKey(videoId), sessionId)
}

export function clearSessionId(videoId: string): void {
  if (typeof window === "undefined") {
    return
  }
  window.localStorage.removeItem(sessionStorageKey(videoId))
}
