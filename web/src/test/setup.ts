import { createElement, type ReactNode } from "react"
import { vi } from "vitest"
import "@testing-library/jest-dom/vitest"

vi.mock("@tanstack/react-router", () => ({
  Link: ({
    to,
    params,
    children,
    className,
  }: {
    to: string
    params?: { videoId?: string }
    children?: ReactNode
    className?: string
  }) => {
    const href =
      to.includes("$videoId") && params?.videoId
        ? to.replace("$videoId", params.videoId)
        : to
    return createElement("a", { href, className }, children)
  },
}))
