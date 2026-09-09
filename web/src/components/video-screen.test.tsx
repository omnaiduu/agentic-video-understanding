import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { ApiError } from "@/lib/api"
import { sampleVideo } from "@/test/fixtures"
import { VideoScreen } from "./video-screen"

describe("VideoScreen", () => {
  it("shows a loading state", () => {
    render(
      <VideoScreen isPending video={undefined} isError={false} error={null} />,
    )
    expect(screen.getByText(/loading video/i)).toBeInTheDocument()
  })

  it("shows an error when FastAPI is down", () => {
    render(
      <VideoScreen
        isPending={false}
        video={undefined}
        isError
        error={new Error("The API is unreachable")}
      />,
    )
    expect(screen.getByText(/could not load this video/i)).toBeInTheDocument()
    expect(screen.queryByText(/Player \(Phase 11\)/)).not.toBeInTheDocument()
  })

  it("shows not found without crashing", () => {
    render(
      <VideoScreen
        isPending={false}
        video={undefined}
        isError
        error={new ApiError(404, "Video not found")}
      />,
    )
    expect(screen.getByText(/video not found/i)).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /back to library/i })).toHaveAttribute(
      "href",
      "/",
    )
  })

  it("shows the watch-and-ask shell for a listed video", () => {
    const video = sampleVideo({
      id: "22222222-2222-2222-2222-222222222222",
      original_filename: "talk.mp4",
      duration_s: 125,
    })
    render(
      <VideoScreen isPending={false} video={video} isError={false} error={null} />,
    )
    expect(screen.getByRole("heading", { name: "talk.mp4" })).toBeInTheDocument()
    expect(screen.getByText("2m 5s")).toBeInTheDocument()
    expect(screen.getByText("Speech index")).toBeInTheDocument()
    expect(screen.getByText(/Player \(Phase 11\)/)).toBeInTheDocument()
    expect(
      screen.getByText(/does not POST chat and never talks to Gemma/i),
    ).toBeInTheDocument()
  })

  it("keeps chat off and shows live index lines while books are building", () => {
    const video = sampleVideo({
      original_filename: "talk.mp4",
      status: "ready",
      transcript_status: "processing",
      visual_status: "pending",
      audio_status: "ready",
      slides_status: "skipped",
    })
    render(
      <VideoScreen isPending={false} video={video} isError={false} error={null} />,
    )
    expect(screen.getByText(/building indexes/i)).toBeInTheDocument()
    expect(screen.getByText("building")).toBeInTheDocument()
    expect(screen.getByText("waiting")).toBeInTheDocument()
    expect(
      screen.getByText(/chat stays off until the indexes are ready/i),
    ).toBeInTheDocument()
  })
})
