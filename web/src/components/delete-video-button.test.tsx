import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { deleteVideo } from "@/lib/api"
import { renderWithQuery } from "@/test/render"
import { DeleteVideoButton } from "./delete-video-button"

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>()
  return {
    ...actual,
    deleteVideo: vi.fn(),
  }
})

const mockedDelete = vi.mocked(deleteVideo)

describe("DeleteVideoButton", () => {
  beforeEach(() => {
    mockedDelete.mockReset()
  })

  it("confirms then deletes", async () => {
    const user = userEvent.setup()
    mockedDelete.mockResolvedValue(undefined)
    const onDeleted = vi.fn()
    renderWithQuery(
      <DeleteVideoButton videoId="vid-1" onDeleted={onDeleted} />,
    )
    await user.click(screen.getByRole("button", { name: /^delete$/i }))
    expect(mockedDelete).not.toHaveBeenCalled()
    expect(
      screen.getByText(/delete this video\? this cannot be undone/i),
    ).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: /confirm delete/i }))
    await waitFor(() => {
      expect(mockedDelete).toHaveBeenCalledWith("vid-1")
    })
    expect(onDeleted).toHaveBeenCalled()
  })

  it("does not delete when confirm is cancelled", async () => {
    const user = userEvent.setup()
    renderWithQuery(<DeleteVideoButton videoId="vid-1" onDeleted={vi.fn()} />)
    await user.click(screen.getByRole("button", { name: /^delete$/i }))
    await user.click(screen.getByRole("button", { name: /cancel/i }))
    expect(mockedDelete).not.toHaveBeenCalled()
    expect(screen.getByRole("button", { name: /^delete$/i })).toBeInTheDocument()
  })
})
