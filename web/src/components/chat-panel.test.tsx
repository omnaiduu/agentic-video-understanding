import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { postChat } from "@/lib/api"
import { sessionStorageKey } from "@/lib/session"
import { renderWithQuery } from "@/test/render"
import { ChatPanel } from "./chat-panel"

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>()
  return {
    ...actual,
    postChat: vi.fn(),
  }
})

const mockedChat = vi.mocked(postChat)

const reply = {
  answer: "A dark frame at 0.1s.",
  citations: [0.1],
  steps: [
    {
      do: "look",
      start_s: 0.1,
      end_s: 0.5,
      ok: true,
      detail: "looked",
    },
    {
      do: "answer",
      start_s: null,
      end_s: null,
      ok: true,
      detail: "",
    },
  ],
  session_id: "sess-1",
  export_url: null,
}

describe("ChatPanel", () => {
  beforeEach(() => {
    mockedChat.mockReset()
    window.localStorage.clear()
  })

  it("asks, shows the answer, and seeks when a time chip is clicked", async () => {
    const user = userEvent.setup()
    mockedChat.mockResolvedValue(reply)
    const onSeek = vi.fn()
    renderWithQuery(
      <ChatPanel videoId="vid-1" locked={false} onSeek={onSeek} />,
    )
    await user.type(screen.getByLabelText(/ask a question/i), "what is at 0.1s?")
    await user.click(screen.getByRole("button", { name: /send/i }))
    expect(await screen.findByText("A dark frame at 0.1s.")).toBeInTheDocument()
    expect(mockedChat).toHaveBeenCalledWith("vid-1", "what is at 0.1s?", null)
    expect(window.localStorage.getItem(sessionStorageKey("vid-1"))).toBe("sess-1")
    expect(screen.queryByLabelText(/exported clip/i)).not.toBeInTheDocument()
    expect(screen.queryByRole("link", { name: /download/i })).not.toBeInTheDocument()
    const details = screen.getByText("Details").closest("details")
    expect(details).not.toHaveAttribute("open")
    await user.click(screen.getByRole("button", { name: "0.1s" }))
    expect(onSeek).toHaveBeenCalledWith(0.1)
  })

  it("reuses the saved session_id on the next question", async () => {
    const user = userEvent.setup()
    window.localStorage.setItem(sessionStorageKey("vid-1"), "sess-1")
    mockedChat.mockResolvedValue({ ...reply, session_id: "sess-1", citations: [] })
    renderWithQuery(
      <ChatPanel videoId="vid-1" locked={false} onSeek={vi.fn()} />,
    )
    await user.type(screen.getByLabelText(/ask a question/i), "and then?")
    await user.click(screen.getByRole("button", { name: /send/i }))
    await waitFor(() => {
      expect(mockedChat).toHaveBeenCalledWith("vid-1", "and then?", "sess-1")
    })
  })

  it("shows Working… and disables send while the request is in flight", async () => {
    const user = userEvent.setup()
    let finish: (value: typeof reply) => void = () => undefined
    mockedChat.mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve
        }),
    )
    renderWithQuery(
      <ChatPanel videoId="vid-1" locked={false} onSeek={vi.fn()} />,
    )
    await user.type(screen.getByLabelText(/ask a question/i), "hello")
    await user.click(screen.getByRole("button", { name: /send/i }))
    expect(await screen.findByText(/working/i)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled()
    finish(reply)
    expect(await screen.findByText("A dark frame at 0.1s.")).toBeInTheDocument()
  })

  it("does not show the form while the video is not ready", () => {
    renderWithQuery(
      <ChatPanel videoId="vid-1" locked onSeek={vi.fn()} />,
    )
    expect(
      screen.getByText(/chat stays off until the video is ready/i),
    ).toBeInTheDocument()
    expect(screen.queryByLabelText(/ask a question/i)).not.toBeInTheDocument()
  })

  it("keeps the form on while indexes are still building", () => {
    renderWithQuery(
      <ChatPanel
        videoId="vid-1"
        locked={false}
        indexesBuilding
        onSeek={vi.fn()}
      />,
    )
    expect(
      screen.getByText(/indexes are still building/i),
    ).toBeInTheDocument()
    expect(screen.getByLabelText(/ask a question/i)).toBeInTheDocument()
  })

  it("plays an exported clip inside the assistant turn", async () => {
    const user = userEvent.setup()
    mockedChat.mockResolvedValue({
      ...reply,
      answer: "Clip is ready.",
      citations: [],
      steps: [
        {
          do: "export_clip",
          start_s: 0,
          end_s: 2,
          ok: true,
          detail: "exported",
        },
        {
          do: "answer",
          start_s: null,
          end_s: null,
          ok: true,
          detail: "",
        },
      ],
      export_url: "/videos/vid/exports/exp-1",
    })
    renderWithQuery(
      <ChatPanel videoId="vid-1" locked={false} onSeek={vi.fn()} />,
    )
    await user.type(screen.getByLabelText(/ask a question/i), "clip that")
    await user.click(screen.getByRole("button", { name: /send/i }))
    expect(await screen.findByText("Clip is ready.")).toBeInTheDocument()
    const player = screen.getByLabelText(/exported clip/i)
    expect(player.tagName).toBe("VIDEO")
    expect(player).toHaveAttribute(
      "src",
      "http://127.0.0.1:8000/videos/vid/exports/exp-1",
    )
    const download = screen.getByRole("link", { name: /download/i })
    expect(download).toHaveAttribute(
      "href",
      "http://127.0.0.1:8000/videos/vid/exports/exp-1",
    )
    expect(screen.getByRole("link", { name: /download/i })).toHaveAttribute(
      "download",
      "clip.mp4",
    )
    expect(document.querySelector("[data-slot='chat-thread']")).toHaveClass(
      "overflow-y-auto",
    )
  })

  it("plays exported audio with an audio element", async () => {
    const user = userEvent.setup()
    mockedChat.mockResolvedValue({
      ...reply,
      answer: "Wav is ready.",
      citations: [],
      steps: [
        {
          do: "export_audio",
          start_s: 0,
          end_s: 2,
          ok: true,
          detail: "exported",
        },
      ],
      export_url: "/videos/vid/exports/exp-wav",
    })
    renderWithQuery(
      <ChatPanel videoId="vid-1" locked={false} onSeek={vi.fn()} />,
    )
    await user.type(screen.getByLabelText(/ask a question/i), "export audio")
    await user.click(screen.getByRole("button", { name: /send/i }))
    const player = await screen.findByLabelText(/exported audio/i)
    expect(player.tagName).toBe("AUDIO")
    expect(screen.getByRole("link", { name: /download/i })).toHaveAttribute(
      "download",
      "audio.wav",
    )
  })

  it("explains a 60 second export cap in the thread", async () => {
    const user = userEvent.setup()
    mockedChat.mockResolvedValue({
      ...reply,
      answer: "Need a shorter window.",
      citations: [],
      steps: [
        {
          do: "export_clip",
          start_s: 0,
          end_s: 600,
          ok: false,
          detail: "requested 600.000s export; cap is 60s. Refuse, do not shrink.",
        },
        {
          do: "answer",
          start_s: null,
          end_s: null,
          ok: true,
          detail: "",
        },
      ],
      export_url: null,
    })
    renderWithQuery(
      <ChatPanel videoId="vid-1" locked={false} onSeek={vi.fn()} />,
    )
    await user.type(screen.getByLabelText(/ask a question/i), "export ten minutes")
    await user.click(screen.getByRole("button", { name: /send/i }))
    expect(
      await screen.findByText(/longer than 60 seconds/i),
    ).toBeInTheDocument()
    expect(screen.queryByLabelText(/exported clip/i)).not.toBeInTheDocument()
  })

  it("explains when Gemma is down", async () => {
    const user = userEvent.setup()
    const { ApiError } = await import("@/lib/api")
    mockedChat.mockRejectedValue(new ApiError(503, "BRAIN=fake has no script"))
    renderWithQuery(
      <ChatPanel videoId="vid-1" locked={false} onSeek={vi.fn()} />,
    )
    await user.type(screen.getByLabelText(/ask a question/i), "hello")
    await user.click(screen.getByRole("button", { name: /send/i }))
    expect(
      await screen.findByText(/language model is not available/i),
    ).toBeInTheDocument()
  })
})
