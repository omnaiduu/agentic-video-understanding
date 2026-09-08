import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { sampleVideo } from "@/test/fixtures"
import { LibraryScreen } from "./library-screen"

describe("LibraryScreen", () => {
  it("shows a loading state", () => {
    render(
      <LibraryScreen
        isPending
        videos={undefined}
        isError={false}
        error={null}
      />,
    )
    expect(screen.getByText(/loading library/i)).toBeInTheDocument()
  })

  it("shows an error when FastAPI is down", () => {
    render(
      <LibraryScreen
        isPending={false}
        videos={undefined}
        isError
        error={new Error("The API is unreachable")}
      />,
    )
    expect(screen.getByText(/could not load videos/i)).toBeInTheDocument()
    expect(screen.getByText(/the api is unreachable/i)).toBeInTheDocument()
    expect(screen.queryByText("demo.mp4")).not.toBeInTheDocument()
  })

  it("shows empty copy when the list is empty", () => {
    render(
      <LibraryScreen isPending={false} videos={[]} isError={false} error={null} />,
    )
    expect(screen.getByText(/no videos yet/i)).toBeInTheDocument()
  })

  it("lists videos from the query result", () => {
    const video = sampleVideo()
    render(
      <LibraryScreen
        isPending={false}
        videos={[video]}
        isError={false}
        error={null}
      />,
    )
    expect(screen.getByText("demo.mp4")).toBeInTheDocument()
    expect(screen.getByText("42s")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /demo.mp4/i })).toHaveAttribute(
      "href",
      `/videos/${video.id}`,
    )
  })
})
