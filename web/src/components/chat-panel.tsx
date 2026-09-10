import { useMutation } from "@tanstack/react-query"
import { useEffect, useRef, useState } from "react"

import { ChatExport } from "@/components/chat-export"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import {
  postChat,
  type ChatOut,
  type ChatStep,
} from "@/lib/api"
import { humanizeChatError } from "@/lib/chat-errors"
import { exportFailureNote, exportKindFromSteps } from "@/lib/export"
import { formatDuration } from "@/lib/format"
import { loadSessionId, saveSessionId } from "@/lib/session"

export type SeekFn = (seconds: number) => void

type Turn = {
  role: "user" | "assistant"
  text: string
  citations?: number[]
  steps?: ChatStep[]
  exportUrl?: string | null
}

function formatStep(step: ChatStep): string {
  const when =
    step.start_s != null && step.end_s != null
      ? ` ${formatDuration(step.start_s)}–${formatDuration(step.end_s)}`
      : ""
  const detail = step.detail ? ` — ${step.detail}` : ""
  const failed = step.ok ? "" : " (failed)"
  return `${step.do}${when}${failed}${detail}`
}

export function ChatPanel({
  videoId,
  locked,
  indexesBuilding = false,
  onSeek,
}: {
  videoId: string
  locked: boolean
  indexesBuilding?: boolean
  onSeek: SeekFn
}) {
  const [draft, setDraft] = useState("")
  const [turns, setTurns] = useState<Turn[]>([])
  const [error, setError] = useState<string | null>(null)
  const sessionRef = useRef<string | null>(null)
  const threadRef = useRef<HTMLOListElement>(null)

  useEffect(() => {
    sessionRef.current = loadSessionId(videoId)
    setTurns([])
    setDraft("")
    setError(null)
  }, [videoId])

  const mutation = useMutation({
    mutationFn: (message: string) =>
      postChat(videoId, message, sessionRef.current),
    retry: false,
    onSuccess: (data: ChatOut, message: string) => {
      sessionRef.current = data.session_id
      saveSessionId(videoId, data.session_id)
      setTurns((prev) => [
        ...prev,
        { role: "user", text: message },
        {
          role: "assistant",
          text: data.answer,
          citations: data.citations,
          steps: data.steps,
          exportUrl: data.export_url,
        },
      ])
    },
    onError: (caught: Error) => {
      setError(humanizeChatError(caught))
    },
  })

  useEffect(() => {
    const node = threadRef.current
    if (!node) {
      return
    }
    node.scrollTop = node.scrollHeight
  }, [turns, mutation.isPending])

  function send() {
    const message = draft.trim()
    if (!message || mutation.isPending || locked) {
      return
    }
    setError(null)
    setDraft("")
    mutation.mutate(message)
  }

  return (
    <Card className="flex max-h-[min(36rem,70vh)] flex-col">
      <CardHeader className="shrink-0">
        <CardTitle>Chat</CardTitle>
      </CardHeader>
      <CardContent className="flex min-h-0 flex-1 flex-col space-y-4">
        {locked ? (
          <p className="text-sm text-muted-foreground">
            Chat stays off until the video is ready.
          </p>
        ) : (
          <>
            {indexesBuilding ? (
              <p className="text-sm text-muted-foreground">
                Indexes are still building. Look and listen work; search may be
                incomplete.
              </p>
            ) : null}
            <ol
              ref={threadRef}
              className="min-h-0 flex-1 space-y-3 overflow-y-auto pr-1"
              data-slot="chat-thread"
            >
              {turns.map((turn, index) => {
                const kind = exportKindFromSteps(turn.steps)
                const failedExport = exportFailureNote(turn.steps)
                return (
                  <li key={`${turn.role}-${index}`} className="space-y-2">
                    <p className="text-xs font-medium text-muted-foreground">
                      {turn.role === "user" ? "You" : "Answer"}
                    </p>
                    <p className="text-sm whitespace-pre-wrap">{turn.text}</p>
                    {turn.citations && turn.citations.length > 0 ? (
                      <div className="flex flex-wrap gap-2">
                        {turn.citations.map((time, chip) => (
                          <Button
                            key={`${time}-${chip}`}
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => onSeek(time)}
                          >
                            {formatDuration(time)}
                          </Button>
                        ))}
                      </div>
                    ) : null}
                    {turn.role === "assistant" && turn.exportUrl ? (
                      <ChatExport path={turn.exportUrl} kind={kind} />
                    ) : null}
                    {turn.role === "assistant" && failedExport ? (
                      <p className="text-sm text-destructive" role="alert">
                        {failedExport}
                      </p>
                    ) : null}
                    {turn.steps && turn.steps.length > 0 ? (
                      <details className="text-sm text-muted-foreground">
                        <summary className="cursor-pointer select-none">
                          Details
                        </summary>
                        <ul className="mt-2 list-disc space-y-1 pl-5">
                          {turn.steps.map((step, stepIndex) => (
                            <li key={`${step.do}-${stepIndex}`}>
                              {formatStep(step)}
                            </li>
                          ))}
                        </ul>
                      </details>
                    ) : null}
                  </li>
                )
              })}
            </ol>
            {mutation.isPending ? (
              <p className="text-sm text-muted-foreground" aria-live="polite">
                Working…
              </p>
            ) : null}
            {error ? (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            ) : null}
            <form
              className="shrink-0 space-y-2"
              onSubmit={(event) => {
                event.preventDefault()
                send()
              }}
            >
              <label className="sr-only" htmlFor="chat-message">
                Ask a question
              </label>
              <Textarea
                id="chat-message"
                value={draft}
                disabled={mutation.isPending}
                placeholder="Ask about this video"
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault()
                    send()
                  }
                }}
              />
              <Button type="submit" disabled={mutation.isPending || !draft.trim()}>
                Send
              </Button>
            </form>
          </>
        )}
      </CardContent>
    </Card>
  )
}
