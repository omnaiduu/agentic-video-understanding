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
  "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&display=swap"

function RootDocument({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <HeadContent />
      </head>
      <body className="relative min-h-screen font-sans antialiased">
        <div
          className="app-grain pointer-events-none fixed inset-0 z-0 opacity-[0.04] mix-blend-overlay"
          aria-hidden
        />
        <div className="relative z-10 flex min-h-screen flex-col">
          <header className="sticky top-0 z-30 border-b border-border/70 bg-background/75 backdrop-blur-xl">
            <div className="mx-auto flex h-14 w-full max-w-7xl items-center px-4 sm:px-6 lg:px-8">
              <Link
                to="/"
                className="flex items-center gap-2.5 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <AppMark />
                <span className="text-sm font-semibold tracking-tight">
                  Agentic Video
                </span>
              </Link>
            </div>
          </header>
          <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6 lg:px-8">
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
        content: "#1c1914",
      },
    ],
    links: [
      {
        rel: "icon",
        href: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%23e8c15a'/%3E%3Cpath d='M12 8.5v15l12-7.5-12-7.5z' fill='%231c1914'/%3E%3C/svg%3E",
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
