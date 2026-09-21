import { cn } from "@/lib/utils"

export function AppMark({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "grid size-7 place-items-center rounded-lg bg-primary text-primary-foreground shadow-[0_0_0_1px_oklch(0.84_0.13_85/0.25)]",
        className,
      )}
      aria-hidden
    >
      <svg viewBox="0 0 24 24" className="size-4 translate-x-px" fill="currentColor">
        <path d="M8.4 5.6v12.8c0 .7.8 1.1 1.4.7l9.2-6.4a.8.8 0 0 0 0-1.4L9.8 4.9a.8.8 0 0 0-1.4.7Z" />
      </svg>
    </span>
  )
}
