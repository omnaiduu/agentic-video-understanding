import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import { VideoScreen } from "@/components/video-screen"
import { getVideo, videoKeys } from "@/lib/api"

export const Route = createFileRoute("/videos/$videoId")({
  component: VideoPage,
})

function VideoPage() {
  const { videoId } = Route.useParams()
  const query = useQuery({
    queryKey: videoKeys.detail(videoId),
    queryFn: () => getVideo(videoId),
    enabled: typeof window !== "undefined",
  })
  return (
    <VideoScreen
      isPending={query.isPending}
      isError={query.isError}
      error={query.error}
      video={query.data}
    />
  )
}
