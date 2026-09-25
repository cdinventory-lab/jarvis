"""Console UI (spec section 17).

A clean futuristic console interface today; the same EventBus renders into a
desktop/web GUI later. Shows:

* JARVIS status (Listening / Thinking / Executing / Verifying / Complete)
* the activity log with timestamps
* speech lines
* the user prompt

Deliberately shows *actions and status only* - never private chain-of-thought
(Phase 2's LLM reasoning stays internal by design).
"""

from __future__ import annotations

import os
import sys

from jarvis.core.events import Event, EventBus, EventKind

_STATUS_SYMBOLS = {
    "listening": "●",
    "thinking": "●",
    "executing": "●",
    "verifying": "●",
    "complete": "✓",
    "error": "✗",
    "paused": "⏸",
    "stopped": "✗",
    "idle": "○",
}

_ANSI = {
    "cyan": "\033[36m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "red": "\033[31m",
    "magenta": "\033[35m",
    "dim": "\033[2m",
    "bold": "\033[1m",
    "reset": "\033[0m",
}

BANNER = r"""
      ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
      ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
      ██║███████║██████╔╝██║   ██║██║███████╗
██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
"""


class ConsoleUI:
    """Renders events from the bus as a clean console activity feed."""

    def __init__(self, events: EventBus, *, use_colors: bool | None = None) -> None:
        self.events = events
        self.use_colors = use_colors if use_colors is not None else self._detect_colors()
        self._last_status: str | None = None
        self._unsubscribe = events.subscribe(self.on_event)

    @staticmethod
    def _detect_colors() -> bool:
        return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None

    def _c(self, text: str, *codes: str) -> str:
        if not self.use_colors:
            return text
        return "".join(_ANSI[code] for code in codes) + text + _ANSI["reset"]

    # ------------------------------------------------------------------- banner

    def banner(self, version: str, backend_name: str, policy_note: str) -> None:
        print(self._c(BANNER, "cyan"))
        print(self._c(f"  JARVIS v{version} - autonomous PC assistant", "bold"))
        print(self._c(f"  backend: {backend_name}   safety: {policy_note}", "dim"))
        print(self._c("  type 'help' for what I can do - 'exit' to quit", "dim"))
        print()

    # -------------------------------------------------------------------- events

    def on_event(self, event: Event) -> None:
        line = self._format(event)
        if line:
            print(line, flush=True)

    def _format(self, event: Event) -> str:
        ts = event.ts.strftime("%H:%M:%S")
        stamp = self._c(f"{ts}  ", "dim")

        if event.kind == EventKind.STATUS:
            status = str(event.data.get("status", ""))
            symbol = _STATUS_SYMBOLS.get(status, "●")
            colored = self._c(
                f"{symbol} {event.message}",
                "green" if status in {"complete", "listening"} else "cyan",
            )
            return f"{stamp}{colored}"

        if event.kind == EventKind.USER_INPUT:
            return f"{stamp}{self._c('User:', 'bold')} {event.message}"

        if event.kind == EventKind.SPEECH:
            return f"{stamp}{self._c('JARVIS:', 'bold')} {self._c(event.message, 'magenta')}"

        if event.kind == EventKind.VERIFICATION:
            ok = event.level != "warning"
            mark = self._c("✓", "green") if ok else self._c("✗", "yellow")
            return f"{stamp}{mark} {event.message}"

        if event.kind == EventKind.ERROR or event.level == "error":
            return f"{stamp}{self._c('✗ ' + event.message, 'red')}"

        if event.kind == EventKind.APPROVAL:
            return f"{stamp}{self._c('⚠ ' + event.message, 'yellow')}"

        if event.kind in {EventKind.ACTIVITY, EventKind.PLAN, EventKind.TOOL_CALL, EventKind.TASK}:
            prefix = {"plan": "◇", "tool_call": "▸", "task": "■"}.get(event.kind.value, "·")
            body = prefix + " " + event.message
            return f"{stamp}{self._c(body, 'cyan') if event.kind == EventKind.PLAN else body}"

        return f"{stamp}{event.message}"

    # ------------------------------------------------------------------- prompt

    def prompt(self) -> str:
        try:
            return input(self._c("JARVIS> ", "bold", "cyan"))
        except EOFError:
            return "exit"

    def close(self) -> None:
        self._unsubscribe()
