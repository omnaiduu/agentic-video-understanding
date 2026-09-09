import { afterEach, describe, expect, it, vi } from "vitest"
import {
  ApiError,
  DEFAULT_MAX_UPLOAD_BYTES,
  getApiBaseUrl,
  getVideo,
  isNotFound,
  isOversize,
  listVideos,
  oversizeMessage,
  uploadVideo,
} from "./api"
import { sampleVideo } from "@/test/fixtures"

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

function jsonResponse(status: number, body: unknown) {
  const text = JSON.stringify(body)
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "Error",
    json: async () => body,
    text: async () => text,
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

describe("uploadVideo", () => {
  it("rejects oversize files without posting a 2 GB fixture", async () => {
    const file = new File(["x"], "huge.mp4", { type: "video/mp4" })
    Object.defineProperty(file, "size", { value: DEFAULT_MAX_UPLOAD_BYTES + 1 })
    const xhr = vi.fn()
    vi.stubGlobal("XMLHttpRequest", xhr)
    await expect(uploadVideo(file)).rejects.toMatchObject({
      name: "ApiError",
      status: 413,
    })
    expect(xhr).not.toHaveBeenCalled()
  })

  it("posts multipart and reports byte progress", async () => {
    const row = sampleVideo()
    vi.stubGlobal(
      "XMLHttpRequest",
      class {
        status = 201
        statusText = "Created"
        responseText = JSON.stringify(row)
        upload: { onprogress: ((event: ProgressEvent) => void) | null } = {
          onprogress: null,
        }
        onload: (() => void) | null = null
        open() {}
        send() {
          this.upload.onprogress?.({
            lengthComputable: true,
            loaded: 40,
            total: 80,
          } as ProgressEvent)
          this.onload?.()
        }
      },
    )
    const percents: number[] = []
    const file = new File(["clip"], "clip.mp4", { type: "video/mp4" })
    await expect(
      uploadVideo(file, (percent) => percents.push(percent)),
    ).resolves.toEqual(row)
    expect(percents).toEqual([50])
  })

  it("surfaces a 413 from FastAPI", async () => {
    vi.stubGlobal(
      "XMLHttpRequest",
      class {
        status = 413
        statusText = "Payload Too Large"
        responseText = JSON.stringify({ detail: "file too large" })
        upload = { onprogress: null }
        onload: (() => void) | null = null
        open() {}
        send() {
          this.onload?.()
        }
      },
    )
    const file = new File(["clip"], "clip.mp4", { type: "video/mp4" })
    await expect(uploadVideo(file)).rejects.toMatchObject({
      name: "ApiError",
      status: 413,
      message: "file too large",
    })
  })
})

describe("oversize helpers", () => {
  it("maps 413 to a readable message", () => {
    const error = new ApiError(413, "file too large")
    expect(isOversize(error)).toBe(true)
    expect(oversizeMessage(error)).toBe("File is too large (2 GB max).")
  })
})
