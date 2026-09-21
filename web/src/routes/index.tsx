import { useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, useNavigate } from "@tanstack/react-router"

import { LibraryScreen } from "@/components/library-screen"
import { UploadPanel } from "@/components/upload-panel"
import { listVideos, videoKeys, type Video } from "@/lib/api"

export const Route = createFileRoute("/")({ component: LibraryPage })

function LibraryPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const query = useQuery({
    queryKey: videoKeys.all,
    queryFn: listVideos,
    enabled: typeof window !== "undefined",
  })

  function handleUploaded(video: Video) {
    queryClient.setQueryData(videoKeys.detail(video.id), video)
    void queryClient.invalidateQueries({ queryKey: videoKeys.all })
    void navigate({ to: "/videos/$videoId", params: { videoId: video.id } })
  }

  return (
    <div className="app-enter space-y-8">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-2xl space-y-2">
          <p className="text-sm font-medium tracking-[0.18em] text-primary uppercase">
            Studio
          </p>
          <h1 className="text-4xl font-semibold tracking-tight text-pretty sm:text-5xl">
            Library
          </h1>
          <p className="text-base text-muted-foreground text-pretty">
            Upload a long video. Indexes build once. Then ask — the model looks at a
            short slice, not the whole file.
          </p>
        </div>
      </div>
      <UploadPanel onUploaded={handleUploaded} />
      <LibraryScreen
        isPending={query.isPending}
        isError={query.isError}
        error={query.error}
        videos={query.data}
      />
    </div>
  )
}
