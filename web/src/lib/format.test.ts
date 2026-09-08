import { describe, expect, it } from "vitest"
import { formatDuration } from "./format"

describe("formatDuration", () => {
  it("returns em dash when duration is unknown", () => {
    expect(formatDuration(null)).toBe("—")
  })

  it("formats short clips in seconds", () => {
    expect(formatDuration(42)).toBe("42s")
    expect(formatDuration(5.2)).toBe("5.2s")
  })

  it("formats minutes and seconds", () => {
    expect(formatDuration(90)).toBe("1m 30s")
    expect(formatDuration(125)).toBe("2m 5s")
  })
})
