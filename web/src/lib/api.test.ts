import { afterEach, describe, expect, it, vi } from "vitest"
import { ApiError, getApiBaseUrl, getVideo, isNotFound, listVideos } from "./api"
import { sampleVideo } from "@/test/fixtures"

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

function jsonResponse(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "Error",
    json: async () => body,
  }
}

describe("getApiBaseUrl", () => {
  it("uses VITE_API_URL when set", () => {
    vi.stubEnv("VITE_API_URL", "http://api.example:9000/")
    expect(getApiBaseUrl()).toBe("http://api.example:9000")
  })

  it("defaults to local FastAPI", () => {
    vi.stubEnv("VITE_API_URL", "")
    expect(getApiBaseUrl()).toBe("http://127.0.0.1:8000")
  })
})

describe("listVideos", () => {
  it("returns an empty list", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(200, [])))
    await expect(listVideos()).resolves.toEqual([])
  })

  it("returns videos from FastAPI", async () => {
    const rows = [sampleVideo()]
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(200, rows)))
    await expect(listVideos()).resolves.toEqual(rows)
  })

  it("throws ApiError when FastAPI returns an error status", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(503, { detail: "nope" })),
    )
    await expect(listVideos()).rejects.toBeInstanceOf(ApiError)
    await expect(listVideos()).rejects.toMatchObject({
      name: "ApiError",
      status: 503,
      message: "nope",
    })
  })

  it("throws ApiError when FastAPI is unreachable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
    )
    await expect(listVideos()).rejects.toMatchObject({
      name: "ApiError",
      status: 0,
      message: "The API is unreachable",
    })
  })
})

describe("getVideo", () => {
  it("returns one video", async () => {
    const row = sampleVideo({
      id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
      original_filename: "talk.mp4",
      duration_s: 90,
    })
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(200, row)))
    await expect(getVideo(row.id)).resolves.toEqual(row)
  })

  it("marks 404 as not found", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(404, { detail: "Video not found" }),
      ),
    )
    try {
      await getVideo("missing")
      throw new Error("expected ApiError")
    } catch (error) {
      expect(isNotFound(error)).toBe(true)
    }
  })
})
