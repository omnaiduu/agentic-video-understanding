import { useMutation } from "@tanstack/react-query"
import { useEffect, useRef, useState } from "react"
import { ArrowUp, Lock } from "lucide-react"

import { ChatExport } from "@/components/chat-export"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardAction,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import {
  postChat,
  type ChatOut,
  type ChatStep,
  type ChatThought,
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
  thoughts?: ChatThought[]
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
  const [thinking, setThinking] = useState(false)
  const sessionRef = useRef<string | null>(null)
  const threadRef = useRef<HTMLOListElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    sessionRef.current = loadSessionId(videoId)
    setTurns([])
    setDraft("")
    setError(null)
    setThinking(false)
  }, [videoId])

  const mutation = useMutation({
    mutationFn: (message: string) =>
      postChat(videoId, message, sessionRef.current, thinking),
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
          thoughts: data.thoughts,
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
    <Card className="flex h-full min-h-[28rem] flex-col gap-0 overflow-hidden rounded-none border-0 bg-transparent py-0 shadow-none ring-0 md:min-h-[min(36rem,70vh)]">
      <CardHeader className="shrink-0 border-b border-border py-3">
        <CardTitle className="text-sm font-medium tracking-tight">Chat</CardTitle>
        {locked ? null : (
          <CardAction>
            <label
              className="flex cursor-pointer items-center gap-2 text-xs font-normal text-muted-foreground"
              htmlFor="chat-thinking"
            >
              <input
                id="chat-thinking"
                type="checkbox"
                className="accent-primary"
                checked={thinking}
                disabled={mutation.isPending}
                onChange={(event) => setThinking(event.target.checked)}
              />
              Thinking
            </label>
          </CardAction>
        )}
      </CardHeader>
      <CardContent className="flex min-h-0 flex-1 flex-col gap-3 pt-3">
        {locked ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-2 px-2 text-center">
            <Lock className="size-4 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Chat stays off until the video is ready.
            </p>
          </div>
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
                        className="rounded-full border border-border bg-background/70 px-2.5 py-1 text-left text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
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
                    className={cn("space-y-2", mine ? "ml-6" : "mr-3")}
                  >
                    <p className="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
                      {turn.role === "user" ? "You" : "Answer"}
                    </p>
                    <p
                      className={cn(
                        "rounded-2xl px-3 py-2 text-sm whitespace-pre-wrap",
                        mine
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted/70 text-foreground",
                      )}
                    >
                      {turn.text}
                    </p>
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
                    {(turn.steps && turn.steps.length > 0) ||
                    (turn.thoughts && turn.thoughts.length > 0) ? (
                      <details className="text-sm text-muted-foreground">
                        <summary className="cursor-pointer select-none">
                          Details
                        </summary>
                        {turn.steps && turn.steps.length > 0 ? (
                          <ul className="mt-2 list-disc space-y-1 pl-5">
                            {turn.steps.map((step, stepIndex) => (
                              <li key={`${step.do}-${stepIndex}`}>
                                {formatStep(step)}
                              </li>
                            ))}
                          </ul>
                        ) : null}
                        {turn.thoughts && turn.thoughts.length > 0 ? (
                          <ul className="mt-2 list-disc space-y-2 pl-5">
                            {turn.thoughts.map((thought, thoughtIndex) => (
                              <li key={`${thought.do}-thought-${thoughtIndex}`}>
                                <span className="font-medium">
                                  thought ({thought.do}):
                                </span>{" "}
                                <span className="whitespace-pre-wrap">
                                  {thought.text}
                                </span>
                              </li>
                            ))}
                          </ul>
                        ) : null}
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
        <CardFooter className="shrink-0 border-t border-border bg-muted/25 py-3">
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
                className="max-h-28 min-h-[3.4rem] field-sizing-fixed resize-none rounded-xl bg-background pr-12"
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
