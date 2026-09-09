import { useMutation } from "@tanstack/react-query"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { deleteVideo } from "@/lib/api"

export function DeleteVideoButton({
  videoId,
  onDeleted,
}: {
  videoId: string
  onDeleted?: () => void
}) {
  const [confirming, setConfirming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const mutation = useMutation({
    mutationFn: () => deleteVideo(videoId),
    retry: false,
    onSuccess: () => {
      setError(null)
      setConfirming(false)
      onDeleted?.()
    },
    onError: (caught: Error) => {
      setError(caught.message || "Could not delete this video.")
    },
  })

  if (confirming) {
    return (
      <div className="space-y-2">
        <p className="text-sm text-muted-foreground">
          Delete this video? This cannot be undone.
        </p>
        <div className="flex flex-wrap gap-2">
          <Button
            disabled={mutation.isPending}
            onClick={() => {
              setError(null)
              mutation.mutate()
            }}
            type="button"
            variant="destructive"
          >
            Confirm delete
          </Button>
          <Button
            disabled={mutation.isPending}
            onClick={() => setConfirming(false)}
            type="button"
            variant="outline"
          >
            Cancel
          </Button>
        </div>
        {error ? (
          <p className="text-sm text-destructive" role="alert">
            {error}
          </p>
        ) : null}
      </div>
    )
  }

  return (
    <div className="space-y-1">
      <Button
        disabled={mutation.isPending}
        onClick={() => {
          setError(null)
          setConfirming(true)
        }}
        type="button"
        variant="destructive"
      >
        Delete
      </Button>
      {error ? (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  )
}
