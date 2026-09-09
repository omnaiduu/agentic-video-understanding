import { describe, expect, it } from "vitest"
import { ApiError } from "@/lib/api"
import { humanizeChatError } from "./chat-errors"

describe("humanizeChatError", () => {
  it("explains a missing language model", () => {
    expect(humanizeChatError(new ApiError(503, "BRAIN=fake has no script"))).toMatch(
      /language model is not available/i,
    )
  })

  it("explains an unreachable API", () => {
    expect(humanizeChatError(new ApiError(0, "The API is unreachable"))).toMatch(
      /start fastapi/i,
    )
  })

  it("explains a 60 second export cap on HTTP errors", () => {
    expect(
      humanizeChatError(
        new ApiError(
          400,
          "requested 600.000s export; cap is 60s. Refuse, do not shrink.",
        ),
      ),
    ).toMatch(/60 seconds/i)
  })
})
