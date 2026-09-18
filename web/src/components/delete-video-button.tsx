import { useMutation } from "@tanstack/react-query"
import { useState } from "react"
import { Trash2 } from "lucide-react"

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

  return (
    <div className="space-y-2">
      <Button
        disabled={mutation.isPending}
        onClick={() => {
          setError(null)
          setConfirming(true)
        }}
        type="button"
        variant="outline"
        className="border-destructive/30 text-destructive hover:bg-destructive/15 hover:text-destructive"
        aria-label="Delete"
      >
        <Trash2 data-icon="inline-start" aria-hidden />
        Delete
      </Button>
      {confirming ? (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4 backdrop-blur-sm"
          role="presentation"
          onClick={() => {
            if (!mutation.isPending) {
              setConfirming(false)
            }
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-video-title"
            className="w-full max-w-sm rounded-lg border border-border bg-card p-5 shadow-lg"
            onClick={(event) => event.stopPropagation()}
          >
            <p id="delete-video-title" className="font-medium tracking-tight">
              Delete this video?
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              Delete this video? This cannot be undone.
            </p>
            <div className="mt-4 flex flex-wrap justify-end gap-2">
              <Button
                disabled={mutation.isPending}
                onClick={() => setConfirming(false)}
                type="button"
                variant="outline"
              >
                Cancel
              </Button>
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
            </div>
            {error ? (
              <p className="mt-3 text-sm text-destructive" role="alert">
                {error}
              </p>
            ) : null}
          </div>
        </div>
      ) : error ? (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  )
}
