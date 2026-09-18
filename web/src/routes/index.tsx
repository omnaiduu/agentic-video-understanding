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
    <div className="app-enter space-y-7">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1.5">
          <p className="text-[11px] font-medium tracking-[0.22em] text-primary/85 uppercase">
            Ask the cut
          </p>
          <h1 className="font-serif text-4xl font-medium tracking-tight text-balance sm:text-5xl">
            Library
          </h1>
        </div>
        <p className="max-w-sm text-sm text-muted-foreground text-pretty">
          Upload a long video. Indexes build once. Then ask — the model looks at a
          short slice, not the whole file.
        </p>
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
