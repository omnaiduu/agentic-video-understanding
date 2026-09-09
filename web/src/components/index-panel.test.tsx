import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { sampleVideo } from "@/test/fixtures"
import { IndexPanel } from "./index-panel"

describe("IndexPanel", () => {
  it("shows waiting, building, ready, and skipped lines", () => {
    render(
      <IndexPanel
        video={sampleVideo({
          status: "ready",
          transcript_status: "pending",
          visual_status: "processing",
          audio_status: "ready",
          slides_status: "skipped",
        })}
      />,
    )
    expect(screen.getByText("Speech index")).toBeInTheDocument()
    expect(screen.getByText("Picture index")).toBeInTheDocument()
    expect(screen.getByText("Sound index")).toBeInTheDocument()
    expect(screen.getByText("Slide index")).toBeInTheDocument()
    expect(screen.getByText("waiting")).toBeInTheDocument()
    expect(screen.getByText("building")).toBeInTheDocument()
    expect(screen.getByText("ready")).toBeInTheDocument()
    expect(screen.getByText("skipped")).toBeInTheDocument()
    expect(screen.getByText(/building indexes/i)).toBeInTheDocument()
  })

  it("flips a book from waiting to ready", () => {
    const pending = sampleVideo({
      transcript_status: "pending",
      visual_status: "ready",
      audio_status: "ready",
    })
    const { rerender } = render(<IndexPanel video={pending} />)
    expect(screen.getByText("waiting")).toBeInTheDocument()
    rerender(
      <IndexPanel video={{ ...pending, transcript_status: "ready" }} />,
    )
    expect(screen.queryByText("waiting")).not.toBeInTheDocument()
    expect(screen.queryByText(/building indexes/i)).not.toBeInTheDocument()
  })

  it("shows error_message on an error book", () => {
    render(
      <IndexPanel
        video={sampleVideo({
          transcript_status: "error",
          error_message: "Whisper failed",
        })}
      />,
    )
    expect(screen.getByText("error")).toBeInTheDocument()
    expect(screen.getByText("Whisper failed")).toBeInTheDocument()
  })
})
