import { describe, expect, it } from "vitest"
import { exportFailureNote, exportFilename, exportKindFromSteps } from "./export"

describe("exportKindFromSteps", () => {
  it("defaults to clip when there is no export step", () => {
    expect(exportKindFromSteps()).toBe("clip")
    expect(exportKindFromSteps([])).toBe("clip")
  })

  it("uses the last export_* step", () => {
    expect(
      exportKindFromSteps([
        { do: "export_clip", start_s: 0, end_s: 2, ok: true, detail: "" },
        { do: "answer", start_s: null, end_s: null, ok: true, detail: "" },
      ]),
    ).toBe("clip")
    expect(
      exportKindFromSteps([
        { do: "export_audio", start_s: 0, end_s: 2, ok: true, detail: "" },
        { do: "answer", start_s: null, end_s: null, ok: true, detail: "" },
      ]),
    ).toBe("audio")
  })
})

describe("exportFilename", () => {
  it("names clip and audio downloads", () => {
    expect(exportFilename("clip")).toBe("clip.mp4")
    expect(exportFilename("audio")).toBe("audio.wav")
  })
})

describe("exportFailureNote", () => {
  it("explains the 60 second cap", () => {
    expect(
      exportFailureNote([
        {
          do: "export_clip",
          start_s: 0,
          end_s: 600,
          ok: false,
          detail: "requested 600.000s export; cap is 60s. Refuse, do not shrink.",
        },
      ]),
    ).toMatch(/60 seconds/i)
  })

  it("is null when export succeeded", () => {
    expect(
      exportFailureNote([
        { do: "export_clip", start_s: 0, end_s: 2, ok: true, detail: "" },
      ]),
    ).toBeNull()
  })
})
