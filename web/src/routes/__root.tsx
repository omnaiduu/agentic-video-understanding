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
  "https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,500;6..72,600&family=Outfit:wght@400;500;600;700&display=swap"

function RootDocument({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <HeadContent />
      </head>
      <body className="min-h-screen font-sans antialiased">
        <div className="relative flex min-h-screen flex-col">
          <header className="sticky top-0 z-30 border-b border-white/5 bg-background/70 backdrop-blur-xl">
            <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4 sm:px-6">
              <Link
                to="/"
                className="group flex items-center gap-2.5 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <AppMark className="transition-transform duration-300 group-hover:scale-105" />
                <span className="flex flex-col leading-none">
                  <span className="text-sm font-semibold tracking-tight">
                    Agentic Video
                  </span>
                  <span className="mt-0.5 hidden text-[11px] text-muted-foreground sm:block">
                    Find the moment. Then look.
                  </span>
                </span>
              </Link>
            </div>
          </header>
          <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6 sm:py-10">
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
        content: "#141824",
      },
    ],
    links: [
      {
        rel: "icon",
        href: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%23e4c36a'/%3E%3Cpath d='M12 8.5v15l12-7.5-12-7.5z' fill='%23231d12'/%3E%3C/svg%3E",
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
