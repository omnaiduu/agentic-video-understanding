import { describe, expect, it } from "vitest"
import { sampleVideo } from "@/test/fixtures"
import {
  bookStatus,
  chatLocked,
  indexTone,
  ingestInProgress,
  shouldPollVideo,
} from "./indexes"

describe("indexTone", () => {
  it("maps API statuses to the live panel words", () => {
    expect(indexTone("pending")).toBe("waiting")
    expect(indexTone("processing")).toBe("building")
    expect(indexTone("ready")).toBe("ready")
    expect(indexTone("skipped")).toBe("skipped")
    expect(indexTone("error")).toBe("error")
  })
})

describe("bookStatus", () => {
  it("treats a missing slide book as skipped", () => {
    expect(
      bookStatus(
        sampleVideo({ slides_status: undefined }),
        "slides_status",
      ),
    ).toBe("skipped")
    expect(bookStatus(sampleVideo(), "slides_status")).toBe("ready")
    expect(
      bookStatus(
        sampleVideo({ slides_status: "processing" }),
        "slides_status",
      ),
    ).toBe("processing")
  })

  it("treats leftover pending slides as skipped once the other books finished", () => {
    expect(
      bookStatus(
        sampleVideo({ slides_status: "pending" }),
        "slides_status",
      ),
    ).toBe("skipped")
    expect(
      bookStatus(
        sampleVideo({
          transcript_status: "processing",
          slides_status: "pending",
        }),
        "slides_status",
      ),
    ).toBe("pending")
  })
})

describe("ingestInProgress", () => {
  it("is true while a book is still pending or building", () => {
    expect(
      ingestInProgress(
        sampleVideo({
          status: "ready",
          transcript_status: "processing",
          visual_status: "pending",
          audio_status: "ready",
        }),
      ),
    ).toBe(true)
  })

  it("stops when every known book is terminal", () => {
    expect(ingestInProgress(sampleVideo())).toBe(false)
    expect(
      ingestInProgress(sampleVideo({ slides_status: "pending" })),
    ).toBe(false)
  })

  it("stops polling after an overall error", () => {
    expect(
      ingestInProgress(
        sampleVideo({
          status: "error",
          transcript_status: "processing",
        }),
      ),
    ).toBe(false)
    expect(
      shouldPollVideo(
        sampleVideo({
          status: "error",
          transcript_status: "processing",
        }),
      ),
    ).toBe(false)
  })
})

describe("chatLocked", () => {
  it("keeps chat off only until the file is playable", () => {
    expect(
      chatLocked(
        sampleVideo({
          status: "ready",
          transcript_status: "processing",
        }),
      ),
    ).toBe(false)
    expect(chatLocked(sampleVideo({ status: "ready" }))).toBe(false)
    expect(chatLocked(sampleVideo({ status: "error" }))).toBe(true)
    expect(
      chatLocked(
        sampleVideo({
          status: "ready",
          slides_status: "pending",
        }),
      ),
    ).toBe(false)
  })
})
