import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import { LibraryScreen } from "@/components/library-screen"
import { listVideos, videoKeys } from "@/lib/api"

export const Route = createFileRoute("/")({ component: LibraryPage })

function LibraryPage() {
  const query = useQuery({
    queryKey: videoKeys.all,
    queryFn: listVideos,
    enabled: typeof window !== "undefined",
  })
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Library</h1>
      <LibraryScreen
        isPending={query.isPending}
        isError={query.isError}
        error={query.error}
        videos={query.data}
      />
    </div>
  )
}
