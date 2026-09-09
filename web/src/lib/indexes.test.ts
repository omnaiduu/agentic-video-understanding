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
  it("treats a missing slide book as skipped until Phase 13", () => {
    const video = sampleVideo()
    expect(bookStatus(video, "slides_status")).toBe("skipped")
    expect(
      bookStatus(
        sampleVideo({ slides_status: "processing" }),
        "slides_status",
      ),
    ).toBe("processing")
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
  it("keeps chat off until the file is ready and indexes finish", () => {
    expect(
      chatLocked(
        sampleVideo({
          status: "ready",
          transcript_status: "processing",
        }),
      ),
    ).toBe(true)
    expect(chatLocked(sampleVideo({ status: "ready" }))).toBe(false)
  })
})
