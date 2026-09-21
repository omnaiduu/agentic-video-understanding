import { describe, expect, it } from "vitest"
import { formatAddedOn, formatDuration } from "./format"

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

describe("formatAddedOn", () => {
  it("formats a calendar day", () => {
    const label = formatAddedOn("2026-04-08T12:00:00Z")
    expect(label.length).toBeGreaterThan(0)
    expect(label).toBe(
      new Date("2026-04-08T12:00:00Z").toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
      }),
    )
  })

  it("returns empty for missing dates", () => {
    expect(formatAddedOn(null)).toBe("")
    expect(formatAddedOn("not-a-date")).toBe("")
  })
})
