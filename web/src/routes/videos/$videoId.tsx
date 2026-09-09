import { useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, useNavigate } from "@tanstack/react-router"

import { VideoScreen } from "@/components/video-screen"
import { getVideo, videoKeys } from "@/lib/api"
import { shouldPollVideo } from "@/lib/indexes"

export const Route = createFileRoute("/videos/$videoId")({
  component: VideoPage,
})

function VideoPage() {
  const { videoId } = Route.useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const query = useQuery({
    queryKey: videoKeys.detail(videoId),
    queryFn: () => getVideo(videoId),
    enabled: typeof window !== "undefined",
    refetchInterval: (query) =>
      shouldPollVideo(query.state.data) ? 1000 : false,
  })

  function handleDeleted() {
    void queryClient.removeQueries({ queryKey: videoKeys.detail(videoId) })
    void queryClient.invalidateQueries({ queryKey: videoKeys.all })
    void navigate({ to: "/" })
  }

  return (
    <VideoScreen
      isPending={query.isPending}
      isError={query.isError}
      error={query.error}
      video={query.data}
      onDeleted={handleDeleted}
    />
  )
}
