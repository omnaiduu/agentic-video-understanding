import { afterEach, describe, expect, it } from "vitest"
import { loadSessionId, saveSessionId, sessionStorageKey } from "./session"

afterEach(() => {
  window.localStorage.clear()
})

describe("session storage", () => {
  it("saves and loads a session id per video", () => {
    expect(loadSessionId("aaa")).toBeNull()
    saveSessionId("aaa", "sess-1")
    saveSessionId("bbb", "sess-2")
    expect(loadSessionId("aaa")).toBe("sess-1")
    expect(loadSessionId("bbb")).toBe("sess-2")
    expect(window.localStorage.getItem(sessionStorageKey("aaa"))).toBe("sess-1")
  })
})
