import { useMutation } from "@tanstack/react-query"
import { useEffect, useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import {
  postChat,
  type ChatOut,
  type ChatStep,
} from "@/lib/api"
import { formatDuration } from "@/lib/format"
import { loadSessionId, saveSessionId } from "@/lib/session"

export type SeekFn = (seconds: number) => void

type Turn = {
  role: "user" | "assistant"
  text: string
  citations?: number[]
  steps?: ChatStep[]
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
  onSeek,
}: {
  videoId: string
  locked: boolean
  onSeek: SeekFn
}) {
  const [draft, setDraft] = useState("")
  const [turns, setTurns] = useState<Turn[]>([])
  const [error, setError] = useState<string | null>(null)
  const sessionRef = useRef<string | null>(null)

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
        },
      ])
    },
    onError: (caught: Error) => {
      setError(caught.message || "Chat failed.")
    },
  })

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
    <Card>
      <CardHeader>
        <CardTitle>Chat</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {locked ? (
          <p className="text-sm text-muted-foreground">
            Chat stays off until the indexes are ready.
          </p>
        ) : (
          <>
            <ol className="space-y-3">
              {turns.map((turn, index) => (
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
              ))}
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
              className="space-y-2"
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
