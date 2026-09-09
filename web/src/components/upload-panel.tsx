import { useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import { Progress, ProgressLabel, ProgressValue } from "@/components/ui/progress"
import {
  ApiError,
  isOversize,
  oversizeMessage,
  uploadVideo,
  type Video,
} from "@/lib/api"

const ACCEPT = ".mp4,.mp3,.wav,.m4a,.aac,.flac,.ogg,.opus,audio/*,video/mp4"

export function UploadPanel({
  onUploaded,
}: {
  onUploaded: (video: Video) => void
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [percent, setPercent] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleFile(file: File) {
    setError(null)
    setPercent(0)
    setBusy(true)
    try {
      const video = await uploadVideo(file, setPercent)
      setPercent(100)
      onUploaded(video)
    } catch (caught) {
      setPercent(null)
      if (isOversize(caught)) {
        setError(oversizeMessage(caught))
      } else if (caught instanceof ApiError) {
        setError(caught.message || "Upload failed.")
      } else {
        setError("Upload failed.")
      }
    } finally {
      setBusy(false)
      if (inputRef.current) {
        inputRef.current.value = ""
      }
    }
  }

  return (
    <div className="space-y-3">
      <input
        ref={inputRef}
        id="library-file"
        type="file"
        className="sr-only"
        accept={ACCEPT}
        disabled={busy}
        aria-label="Choose file"
        onChange={(event) => {
          const file = event.target.files?.[0]
          if (file) {
            void handleFile(file)
          }
        }}
      />
      <div className="flex flex-wrap items-center gap-3">
        <Button
          type="button"
          disabled={busy}
          onClick={() => inputRef.current?.click()}
        >
          Choose file
        </Button>
        <p className="text-sm text-muted-foreground">
          mp4 or audio, up to 2 GB. The API stores the file; this page does not
          run models.
        </p>
      </div>
      {percent !== null ? (
        <Progress value={percent} className="max-w-md">
          <ProgressLabel>Uploading</ProgressLabel>
          <ProgressValue />
        </Progress>
      ) : null}
      {error ? (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  )
}
