"""JARVIS command-line interface.

Usage:
    jarvis                          interactive REPL (typed commands)
    jarvis "open notepad and ..."   one-shot command
    jarvis --demo notepad           run a built-in Phase-1 demonstration
    jarvis --doctor                 environment / capability report
    jarvis --list-apps / --list-tools
"""

from __future__ import annotations

import argparse
import importlib.util
import logging
import os
import platform
import shutil
import sys

from jarvis import __version__
from jarvis.app import build_assistant, interactive_approver
from jarvis.config.settings import Settings
from jarvis.core.events import EventBus, EventKind
from jarvis.core.log import setup_logging
from jarvis.core.status import AgentStatus, TaskStatus
from jarvis.ui import ConsoleUI

logger = logging.getLogger("jarvis.cli")

DEMOS: dict[str, str] = {
    "notepad": "Open Notepad and type Hello JARVIS.",
    "search": "Open Chrome and search for Blender clothing mockups.",
    "folder": "Create a folder named Jarvis Demo in my Documents and open it.",
}

EXIT_CODES = {
    TaskStatus.COMPLETED: 0,
    TaskStatus.NEEDS_USER: 2,
    TaskStatus.FAILED: 3,
    TaskStatus.INTERRUPTED: 4,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jarvis",
        description="JARVIS - autonomous PC assistant (Phase 1: computer control)",
    )
    parser.add_argument("command", nargs="*", help="one-shot command text")
    parser.add_argument("--backend", choices=("auto", "simulated", "pyautogui"),
                        help="override the computer backend")
    parser.add_argument("--demo", choices=sorted(DEMOS), help="run a built-in demo")
    parser.add_argument("--assume-yes", action="store_true",
                        help="auto-approve MEDIUM-risk actions (scripted runs)")
    parser.add_argument("--doctor", action="store_true",
                        help="print an environment / capability report and exit")
    parser.add_argument("--list-apps", action="store_true")
    parser.add_argument("--list-tools", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--version", action="version", version=f"jarvis {__version__}")
    return parser


# --------------------------------------------------------------------------- #
# Doctor
# --------------------------------------------------------------------------- #


def _have(module: str) -> str:
    return "yes" if importlib.util.find_spec(module) else "no"


def run_doctor(settings: Settings) -> int:
    print("JARVIS environment report")
    print("-" * 60)
    print(f"OS                : {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Python            : {platform.python_version()}")
    print(f"Platform          : {sys.platform}")
    print(f"Display           : {'yes' if sys.platform == 'win32' else (os.environ.get('DISPLAY') or 'no (headless)')}")
    print(f"pyautogui         : {_have('pyautogui')}")
    print(f"pygetwindow (win) : {_have('pygetwindow')} (window control, Windows)")
    print(f"psutil            : {_have('psutil')} (process checks)")
    print(f"pyperclip         : {_have('pyperclip')} (clipboard)")
    print(f"keyboard          : {_have('keyboard')} (emergency hotkey)")
    print(f"Pillow            : {_have('PIL')} (screenshots/OCR images)")
    print(f"pytesseract       : {_have('pytesseract')} (OCR engine)")
    print(f"tesseract binary  : {shutil.which('tesseract') or 'not found'}")
    print("Audio devices     : unknown (voice arrives in Phase 4)")
    print("-" * 60)
    summary = settings.safe_summary()
    for key in ("backend", "auto_approve_risk", "emergency_stop_hotkey", "data_dir"):
        print(f"{key:17}: {summary[key]}")
    print("-" * 60)
    print("Backend plan: 'auto' uses real control when available, else simulated.")
    return 0


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    overrides: dict[str, str] = {}
    if args.backend:
        overrides["backend"] = args.backend
    if args.assume_yes:
        overrides["assume_yes"] = "true"
    if args.verbose:
        overrides["verbose"] = "true"

    try:
        settings = Settings.load(env=overrides)
    except Exception as exc:  # noqa: BLE001 - config errors must be readable
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    settings = settings.with_overrides(verbose=args.verbose or settings.verbose)

    if args.doctor:
        return run_doctor(settings)

    setup_logging(settings, console=settings.verbose)

    if args.list_apps or args.list_tools:
        from jarvis.control.apps import APP_REGISTRY

        if args.list_apps:
            print("Known applications:")
            for spec in sorted(APP_REGISTRY.values(), key=lambda s: s.name):
                print(f"  {spec.name:<12} ({spec.display})  aliases: {', '.join(spec.aliases)}")
        if args.list_tools:
            events = EventBus()
            assistant = build_assistant(
                settings.with_overrides(backend="simulated"), events=events
            )
            print("Registered tools:")
            for tool in assistant.tools.all():
                print(f"  {tool.name:<16} [{tool.category:<9}] risk={tool.risk.label:<6} {tool.description}")  # noqa: E501
        return 0

    interactive = not args.command and args.demo is None
    events = EventBus()
    assistant = build_assistant(settings, events=events)

    if interactive:
        # Only interactive runs get an interactive approver.
        assistant.security.approver = interactive_approver()
        return _repl(assistant)

    ui = ConsoleUI(events)
    _register_emergency_hotkey(assistant, ui)

    if args.demo:
        command = DEMOS[args.demo]
        print(f"\n  Demo: {command!r}\n")
    else:
        command = " ".join(args.command).strip()

    result = assistant.orchestrator.execute(command)
    ui.close()
    return EXIT_CODES.get(result.status, 1)


def _repl(assistant) -> int:
    """Interactive read-eval-print loop with typed commands."""
    from jarvis.ui import ConsoleUI as UI

    ui = UI(assistant.events)
    ui.banner(
        __version__,
        getattr(assistant.backend, "name", "?"),
        f"auto-approve <= {assistant.settings.auto_approve_risk.label} risk",
    )
    _register_emergency_hotkey(assistant, ui)
    assistant.events.emit(EventKind.STATUS, "Listening", status=AgentStatus.LISTENING.value)

    while True:
        line = ui.prompt()
        text = line.strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in {"exit", "quit"}:
            print("Goodbye.")
            break
        if lowered == "tools":
            for tool in assistant.tools.all():
                print(f"  {tool.name:<16} [{tool.category}] {tool.description}")
            continue
        if lowered == "apps":
            from jarvis.control.apps import APP_REGISTRY

            for spec in sorted(APP_REGISTRY.values(), key=lambda s: s.name):
                print(f"  {spec.name:<12} {spec.display}")
            continue
        if lowered == "memory":
            view = assistant.memory.state_view()
            print(f"  task      : {view.task or '(none)'}")
            print(f"  status    : {view.status.label}")
            print(f"  completed : {view.completed or '[]'}")
            print(f"  remaining : {view.remaining or '[]'}")
            continue

        try:
            result = assistant.orchestrator.execute(text)
            if result.status == TaskStatus.INTERRUPTED:
                assistant.interrupt.clear()
        except KeyboardInterrupt:
            # Second Ctrl+C inside a task is caught by the orchestrator;
            # at the prompt it means "exit".
            assistant.interrupt.clear()
            print("\n(Ctrl+C again during a task stops it; type 'exit' to quit)")
            continue
        assistant.events.emit(EventKind.STATUS, "Listening", status=AgentStatus.LISTENING.value)

    ui.close()
    return 0


def _register_emergency_hotkey(assistant, ui) -> None:
    """CTRL+ALT+J (configurable) stops the agent instantly (spec section 14)."""
    settings = assistant.settings
    if not settings.emergency_hotkey_enabled:
        return
    if importlib.util.find_spec("keyboard") is None:
        logger.debug("keyboard lib not installed - emergency hotkey disabled")
        return
    try:
        import keyboard

        keyboard.add_hotkey(
            settings.emergency_stop_hotkey,
            lambda: (
                assistant.interrupt.request_stop("emergency hotkey pressed"),
                assistant.events.emit(
                    EventKind.STATUS, "Stopped", status=AgentStatus.STOPPED.value
                ),
            ),
        )
        logger.info("emergency hotkey registered: %s", settings.emergency_stop_hotkey)
    except Exception as exc:  # noqa: BLE001 - hotkey is best effort
        logger.warning("could not register emergency hotkey: %s", exc)


if __name__ == "__main__":
    sys.exit(main())
