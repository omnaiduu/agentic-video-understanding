import type { ReactNode } from "react"
import {
  HeadContent,
  Link,
  Scripts,
  createRootRouteWithContext,
} from "@tanstack/react-router"
import appCss from "../styles.css?url"
import type { QueryClient } from "@tanstack/react-query"

import { AppMark } from "@/components/app-mark"

interface MyRouterContext {
  queryClient: QueryClient
}

const FONT_HREF =
  "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&display=swap"

function RootDocument({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body className="min-h-screen font-sans antialiased">
        <div className="flex min-h-screen flex-col">
          <header className="sticky top-0 z-30 border-b border-border bg-background/90 backdrop-blur-md">
            <div className="mx-auto flex h-12 w-full max-w-6xl items-center px-4 sm:px-6">
              <Link
                to="/"
                className="flex items-center gap-2 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <AppMark />
                <span className="text-sm font-medium tracking-tight">
                  Agentic Video
                </span>
              </Link>
            </div>
          </header>
          <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6">
            {children}
          </main>
        </div>
        <Scripts />
      </body>
    </html>
  )
}

export const Route = createRootRouteWithContext<MyRouterContext>()({
  head: () => ({
    meta: [
      {
        charSet: "utf-8",
      },
      {
        name: "viewport",
        content: "width=device-width, initial-scale=1",
      },
      {
        title: "Agentic Video",
      },
      {
        name: "description",
        content:
          "Ask questions about long videos without dumping the whole file into a model.",
      },
      {
        name: "theme-color",
        content: "#f6f5f2",
      },
    ],
    links: [
      {
        rel: "icon",
        href: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%23171717'/%3E%3Cpath d='M12 8.5v15l12-7.5-12-7.5z' fill='%23f6f5f2'/%3E%3C/svg%3E",
      },
      {
        rel: "stylesheet",
        href: appCss,
      },
      {
        rel: "stylesheet",
        href: FONT_HREF,
      },
      {
        rel: "preconnect",
        href: "https://fonts.googleapis.com",
      },
      {
        rel: "preconnect",
        href: "https://fonts.gstatic.com",
        crossOrigin: "anonymous",
      },
    ],
  }),
  shellComponent: RootDocument,
})
