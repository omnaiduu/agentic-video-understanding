import { describe, expect, it } from "vitest"
import { posterTime } from "./media-poster"

describe("posterTime", () => {
  it("picks a later still than the opening frame on long videos", () => {
    expect(posterTime(596)).toBe(12)
    expect(posterTime(8)).toBeGreaterThan(0.8)
  })

  it("falls back when duration is unknown", () => {
    expect(posterTime(null)).toBe(0.4)
  })
})
