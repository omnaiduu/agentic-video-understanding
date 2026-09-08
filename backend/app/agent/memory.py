"""Last 3 time windows as text. Pointers, not old photos."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


MAX_LAST_TIMES = 3
WINDOW_DOS = frozenset(
    {
        "look",
        "listen",
        "search",
        "search_visual",
        "search_audio",
        "export_clip",
        "export_audio",
    }
)
HISTORY_KINDS = frozenset({"question", "answer"})


@dataclass(frozen=True)
class TimeWindow:
    start_s: float
    end_s: float
    kind: str

    def as_dict(self) -> dict[str, Any]:
        return {"start_s": self.start_s, "end_s": self.end_s, "kind": self.kind}


def window_from_mapping(raw: Any) -> TimeWindow | None:
    if not isinstance(raw, dict):
        return None
    kind = raw.get("kind")
    start_s = raw.get("start_s")
    end_s = raw.get("end_s")
    if not isinstance(kind, str) or not kind:
        return None
    try:
        start = float(start_s)
        end = float(end_s)
    except (TypeError, ValueError):
        return None
    return TimeWindow(start_s=start, end_s=end, kind=kind)


def collect_windows(steps: list[Any]) -> list[TimeWindow]:
    windows: list[TimeWindow] = []
    for step in steps:
        if not getattr(step, "ok", False):
            continue
        kind = getattr(step, "do", None)
        if kind not in WINDOW_DOS:
            continue
        start_s = getattr(step, "start_s", None)
        end_s = getattr(step, "end_s", None)
        if start_s is None or end_s is None:
            continue
        windows.append(TimeWindow(start_s=float(start_s), end_s=float(end_s), kind=str(kind)))
    return windows


def push_windows(
    existing: list[dict[str, Any]] | None,
    new: list[TimeWindow],
) -> list[dict[str, Any]]:
    merged: list[TimeWindow] = []
    for item in existing or []:
        window = window_from_mapping(item)
        if window is not None:
            merged.append(window)
    merged.extend(new)
    return [window.as_dict() for window in merged[-MAX_LAST_TIMES:]]


def format_window(window: TimeWindow) -> str:
    if abs(window.end_s - window.start_s) < 1e-6:
        return f"{window.kind} {window.start_s:.2f}s"
    return f"{window.kind} {window.start_s:.2f}s–{window.end_s:.2f}s"


def memory_text(
    history: list[tuple[str, str]] | None,
    last_times: list[dict[str, Any]] | None,
) -> str:
    parts: list[str] = []
    if history:
        parts.append(
            "Previous turns (text only; old photos and audio are not attached):"
        )
        for role, content in history:
            label = "User" if role == "user" else "Assistant"
            parts.append(f"{label}: {content}")
    windows = [
        window
        for window in (window_from_mapping(item) for item in (last_times or []))
        if window is not None
    ]
    if windows:
        parts.append(
            "Last time windows (use these first for \"that\" / \"there\" / "
            "\"the clip\" / \"that frame\"; do not search the whole tape from scratch):"
        )
        for index, window in enumerate(windows, start=1):
            parts.append(f"{index}. {format_window(window)}")
    return "\n".join(parts)
