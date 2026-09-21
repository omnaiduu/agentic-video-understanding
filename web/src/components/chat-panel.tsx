import { useMutation } from "@tanstack/react-query"
import { useEffect, useRef, useState } from "react"
import { ArrowUp, Lock } from "lucide-react"

import { ChatExport } from "@/components/chat-export"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
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
import { cn } from "@/lib/utils"

export type SeekFn = (seconds: number) => void

type Turn = {
  role: "user" | "assistant"
  text: string
  citations?: number[]
  steps?: ChatStep[]
  exportUrl?: string | null
}

const SUGGESTIONS = [
  "What is in the opening shot?",
  "Clip the first 5 seconds",
  "Was there a bird or a red light?",
]

function formatStep(step: ChatStep): string {
  const when =
    step.start_s != null && step.end_s != null
      ? ` ${formatDuration(step.start_s)}–${formatDuration(step.end_s)}`
      : ""
  const detail = step.detail ? ` — ${step.detail}` : ""
  const failed = step.ok ? "" : " (failed)"
  return `${step.do}${when}${failed}${detail}`
}

function WorkingDots() {
  return (
    <span className="inline-flex items-center gap-1" aria-hidden>
      <span className="typing-dot size-1.5 rounded-full bg-live" />
      <span className="typing-dot size-1.5 rounded-full bg-live" />
      <span className="typing-dot size-1.5 rounded-full bg-live" />
    </span>
  )
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
  const threadRef = useRef<HTMLOListElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

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
    onSuccess: (data: ChatOut) => {
      sessionRef.current = data.session_id
      saveSessionId(videoId, data.session_id)
      setTurns((prev) => [
        ...prev,
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

  function send(fromDraft = draft) {
    const message = fromDraft.trim()
    if (!message || mutation.isPending || locked) {
      return
    }
    setError(null)
    setDraft("")
    setTurns((prev) => [...prev, { role: "user", text: message }])
    mutation.mutate(message)
  }

  return (
    <Card className="flex h-full min-h-[22rem] flex-1 flex-col gap-0 overflow-hidden rounded-none border-0 bg-transparent py-0 shadow-none ring-0 md:min-h-0">
      <CardHeader className="shrink-0 border-b border-border py-2.5">
        <CardTitle className="text-sm font-medium">Chat</CardTitle>
      </CardHeader>
      <CardContent className="flex min-h-0 flex-1 flex-col gap-3 pt-3">
        {locked ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-2 px-2 text-center">
            <Lock className="size-4 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Chat stays off until the indexes are ready.
            </p>
          </div>
        ) : (
          <>
            <ol
              ref={threadRef}
              className="thin-scroll min-h-0 flex-1 space-y-3 overflow-y-auto pr-1 pb-1"
              data-slot="chat-thread"
            >
              {turns.length === 0 && !mutation.isPending ? (
                <li className="flex flex-col gap-3 pt-1">
                  <p className="text-sm text-muted-foreground">
                    Ask about speech, a silent visual, a sound, or a clip.
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {SUGGESTIONS.map((hint) => (
                      <button
                        key={hint}
                        type="button"
                        className="rounded-md border border-border bg-background px-2.5 py-1 text-left text-xs text-muted-foreground hover:border-foreground/30 hover:text-foreground"
                        onClick={() => {
                          setDraft(hint)
                          inputRef.current?.focus()
                        }}
                      >
                        {hint}
                      </button>
                    ))}
                  </div>
                </li>
              ) : null}
              {turns.map((turn, index) => {
                const kind = exportKindFromSteps(turn.steps)
                const failedExport = exportFailureNote(turn.steps)
                const mine = turn.role === "user"
                return (
                  <li
                    key={`${turn.role}-${index}`}
                    className={cn("space-y-1.5", mine ? "ml-8" : "mr-3")}
                  >
                    <p className="px-1 text-[11px] font-medium text-muted-foreground">
                      {turn.role === "user" ? "You" : "Answer"}
                    </p>
                    <div
                      className={cn(
                        "rounded-lg px-3 py-2 text-sm leading-relaxed whitespace-pre-wrap",
                        mine
                          ? "bg-foreground text-background"
                          : "bg-muted",
                      )}
                    >
                      <p>{turn.text}</p>
                    </div>
                    {turn.citations && turn.citations.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5 pt-0.5">
                        {turn.citations.map((time, chip) => (
                          <Button
                            key={`${time}-${chip}`}
                            type="button"
                            variant="outline"
                            size="sm"
                            className="h-7 font-mono text-xs"
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
                      <details className="px-1 text-xs text-muted-foreground">
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
              <p
                className="flex items-center gap-2 text-sm text-muted-foreground"
                aria-live="polite"
              >
                <WorkingDots />
                Working…
              </p>
            ) : null}
            {error ? (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            ) : null}
          </>
        )}
      </CardContent>
      {locked ? null : (
        <CardFooter className="shrink-0 border-border bg-muted/40 py-3">
          <form
            className="w-full"
            onSubmit={(event) => {
              event.preventDefault()
              send()
            }}
          >
            <label className="sr-only" htmlFor="chat-message">
              Ask a question
            </label>
            <div className="relative">
              <Textarea
                ref={inputRef}
                id="chat-message"
                value={draft}
                disabled={mutation.isPending}
                placeholder="Ask about this video"
                className="max-h-28 min-h-[3.25rem] field-sizing-fixed resize-none rounded-md bg-background pr-11"
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault()
                    send()
                  }
                }}
              />
              <Button
                type="submit"
                size="icon-sm"
                disabled={mutation.isPending || !draft.trim()}
                className="absolute right-2 bottom-2"
                aria-label="Send"
              >
                <ArrowUp />
                <span className="sr-only">Send</span>
              </Button>
            </div>
          </form>
        </CardFooter>
      )}
    </Card>
  )
}
