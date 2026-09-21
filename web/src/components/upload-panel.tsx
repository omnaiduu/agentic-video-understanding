import { useRef, useState } from "react"
import { Upload } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Progress, ProgressLabel, ProgressValue } from "@/components/ui/progress"
import {
  ApiError,
  isOversize,
  oversizeMessage,
  uploadVideo,
  type Video,
} from "@/lib/api"
import { cn } from "@/lib/utils"

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
  const [over, setOver] = useState(false)
  const [name, setName] = useState<string | null>(null)

  async function handleFile(file: File) {
    setError(null)
    setName(file.name)
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
      setOver(false)
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
      <div
        className={cn(
          "rounded-2xl border border-dashed border-foreground/18 bg-card/70 px-6 py-8 shadow-[inset_0_1px_0_oklch(1_0_0/0.04)] transition-colors",
          over && "border-primary bg-primary/8",
          busy && "border-solid border-primary/40",
        )}
        onDragEnter={(event) => {
          event.preventDefault()
          if (!busy) {
            setOver(true)
          }
        }}
        onDragOver={(event) => {
          event.preventDefault()
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(event) => {
          event.preventDefault()
          setOver(false)
          const file = event.dataTransfer.files?.[0]
          if (file && !busy) {
            void handleFile(file)
          }
        }}
      >
        <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-w-0 items-start gap-3">
            <span className="mt-0.5 grid size-12 shrink-0 place-items-center rounded-xl bg-muted text-primary">
              <Upload className="size-5" />
            </span>
            <div className="min-w-0">
              <p className="text-base font-medium">
                {busy ? name || "Uploading" : "Drop a file here"}
              </p>
              <p className="mt-1 text-base text-muted-foreground">
                mp4 or audio, up to 2 GB. The API stores the file; this page does not
                run models.
              </p>
            </div>
          </div>
          <Button
            type="button"
            disabled={busy}
            onClick={() => inputRef.current?.click()}
            size="lg"
            className="shrink-0"
          >
            Choose file
          </Button>
        </div>
        {percent !== null ? (
          <Progress value={percent} className="relative mt-4">
            <ProgressLabel>Uploading</ProgressLabel>
            <ProgressValue />
          </Progress>
        ) : null}
      </div>
      {error ? (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  )
}
