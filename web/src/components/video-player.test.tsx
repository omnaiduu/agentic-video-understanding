import { describe, expect, it, vi } from "vitest"
import { sampleVideo } from "@/test/fixtures"
import { VideoPlayer } from "./video-player"

describe("VideoPlayer", () => {
  it("gives the parent a seek function that calls Video.js currentTime", async () => {
    const videojs = (await import("video.js")).default as unknown as ReturnType<
      typeof vi.fn
    >
    const player = {
      currentTime: vi.fn(),
      dispose: vi.fn(),
    }
    videojs.mockReturnValue(player)
    const video = sampleVideo()
    let seek: ((seconds: number) => void) | undefined
    const { unmount } = (await import("@testing-library/react")).render(
      <VideoPlayer
        video={video}
        onReady={(fn) => {
          seek = fn
        }}
      />,
    )
    await vi.waitFor(() => {
      expect(seek).toBeTypeOf("function")
    })
    seek?.(12.5)
    expect(player.currentTime).toHaveBeenCalledWith(12.5)
    expect(videojs).toHaveBeenCalledWith(
      expect.any(HTMLVideoElement),
      expect.objectContaining({
        controlBar: {
          children: [
            "playToggle",
            "volumePanel",
            "progressControl",
            "currentTimeDisplay",
            "timeDivider",
            "durationDisplay",
            "pictureInPictureToggle",
            "fullscreenToggle",
          ],
        },
      }),
    )
    expect(videojs.mock.calls[0]?.[1]?.controlBar?.children).not.toContain(
      "remainingTimeDisplay",
    )
    unmount()
    expect(player.dispose).toHaveBeenCalled()
  })
})
