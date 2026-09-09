import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { ApiError, uploadVideo } from "@/lib/api"
import { sampleVideo } from "@/test/fixtures"
import { UploadPanel } from "./upload-panel"

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>()
  return {
    ...actual,
    uploadVideo: vi.fn(),
  }
})

const mockedUpload = vi.mocked(uploadVideo)

describe("UploadPanel", () => {
  beforeEach(() => {
    mockedUpload.mockReset()
  })

  it("uploads a chosen file and reports progress", async () => {
    const user = userEvent.setup()
    const uploaded = sampleVideo({ original_filename: "clip.mp4" })
    mockedUpload.mockImplementation(async (_file, onProgress) => {
      onProgress?.(40)
      return uploaded
    })
    const onUploaded = vi.fn()
    render(<UploadPanel onUploaded={onUploaded} />)
    const file = new File(["bytes"], "clip.mp4", { type: "video/mp4" })
    await user.upload(screen.getByLabelText(/choose file/i), file)
    await waitFor(() => {
      expect(onUploaded).toHaveBeenCalledWith(uploaded)
    })
    expect(mockedUpload).toHaveBeenCalledTimes(1)
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "100")
    expect(screen.getByText("Uploading")).toBeInTheDocument()
  })

  it("shows a readable 413", async () => {
    const user = userEvent.setup()
    mockedUpload.mockRejectedValue(new ApiError(413, "file too large"))
    render(<UploadPanel onUploaded={vi.fn()} />)
    const file = new File(["bytes"], "clip.mp4", { type: "video/mp4" })
    await user.upload(screen.getByLabelText(/choose file/i), file)
    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent("File is too large (2 GB max).")
    expect(screen.queryByText(/player/i)).not.toBeInTheDocument()
  })
})
