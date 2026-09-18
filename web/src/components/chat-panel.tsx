import { useMutation } from "@tanstack/react-query"
import { useEffect, useRef, useState } from "react"
import { ArrowUp, Lock } from "lucide-react"

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
  "What did they say about pricing?",
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
    <Card className="flex h-[min(36rem,70vh)] flex-col border-white/5 bg-card/80 shadow-none ring-1 ring-white/6 md:h-[min(42rem,calc(100vh-11rem))]">
      <CardHeader className="shrink-0 border-b border-white/5">
        <CardTitle className="text-sm font-medium tracking-tight">Chat</CardTitle>
      </CardHeader>
      <CardContent className="flex min-h-0 flex-1 flex-col space-y-4 pt-4">
        {locked ? (
          <div className="flex flex-1 flex-col items-start justify-center gap-2 py-6">
            <span className="grid size-10 place-items-center rounded-2xl bg-muted text-muted-foreground">
              <Lock className="size-4" />
            </span>
            <p className="text-sm text-muted-foreground">
              Chat stays off until the indexes are ready.
            </p>
          </div>
        ) : (
          <>
            <ol
              ref={threadRef}
              className="thin-scroll min-h-0 flex-1 space-y-3 overflow-y-auto pr-1"
              data-slot="chat-thread"
            >
              {turns.length === 0 && !mutation.isPending ? (
                <li className="space-y-3 py-2">
                  <p className="text-sm text-muted-foreground">
                    Ask about speech, a silent visual, a sound, or a clip.
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {SUGGESTIONS.map((hint) => (
                      <button
                        key={hint}
                        type="button"
                        className="rounded-full border border-white/8 bg-background/40 px-3 py-1.5 text-left text-xs text-muted-foreground transition-colors hover:border-primary/30 hover:text-foreground"
                        onClick={() => setDraft(hint)}
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
                    className={cn(
                      "app-enter space-y-2",
                      mine ? "ml-6" : "mr-4",
                    )}
                  >
                    <p className="text-xs font-medium text-muted-foreground">
                      {turn.role === "user" ? "You" : "Answer"}
                    </p>
                    <div
                      className={cn(
                        "rounded-2xl px-3 py-2 text-sm whitespace-pre-wrap",
                        mine
                          ? "bg-primary/12 text-foreground"
                          : "bg-background/55 ring-1 ring-white/6",
                      )}
                    >
                      <p>{turn.text}</p>
                    </div>
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
              <div className="relative">
                <Textarea
                  id="chat-message"
                  value={draft}
                  disabled={mutation.isPending}
                  placeholder="Ask about this video"
                  className="min-h-20 resize-none pr-12"
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
          </>
        )}
      </CardContent>
    </Card>
  )
}
