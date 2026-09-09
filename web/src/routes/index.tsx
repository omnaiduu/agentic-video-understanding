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
    <div className="space-y-6">
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">Library</h1>
        <UploadPanel onUploaded={handleUploaded} />
      </div>
      <LibraryScreen
        isPending={query.isPending}
        isError={query.isError}
        error={query.error}
        videos={query.data}
      />
    </div>
  )
}
