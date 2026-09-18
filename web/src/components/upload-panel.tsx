import { useRef, useState } from "react"
import { FileUp } from "lucide-react"

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
          "relative overflow-hidden rounded-3xl border border-dashed border-white/14 bg-card/40 p-6 transition-all duration-300 sm:p-8",
          over && "border-primary/60 bg-primary/8 glow-ring",
          busy && "border-solid border-white/10",
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
        <div className="pointer-events-none absolute inset-0 poster-scan opacity-20" />
        <div className="relative flex flex-col items-start gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-4">
            <span className="grid size-14 place-items-center rounded-2xl bg-primary/12 text-primary shadow-[0_0_40px_-12px_oklch(0.84_0.12_88)]">
              <FileUp className="size-6" />
            </span>
            <div className="space-y-1.5">
              <p className="text-base font-medium tracking-tight">
                {busy ? name || "Uploading" : "Drop a talk, or choose a file"}
              </p>
              <p className="max-w-md text-sm text-muted-foreground">
                mp4 or audio, up to 2 GB. The API stores the file; this page does not
                run models.
              </p>
            </div>
          </div>
          <Button
            type="button"
            size="lg"
            disabled={busy}
            onClick={() => inputRef.current?.click()}
            className="shrink-0"
          >
            Choose file
          </Button>
        </div>
        {percent !== null ? (
          <Progress value={percent} className="relative mt-6">
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
