"""Composition root: wires every component together.

One place that knows how the pieces connect - the CLI and the tests both use
`build_assistant`, so what is tested is exactly what runs.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from jarvis.config.settings import Settings
from jarvis.control.apps import AppLauncher
from jarvis.control.backends import create_backend
from jarvis.control.filesystem import FilesystemController
from jarvis.control.keyboard import KeyboardController
from jarvis.control.mouse import MouseController
from jarvis.control.terminal import TerminalRunner
from jarvis.control.windows import WindowController
from jarvis.core.brain import RuleBasedBrain
from jarvis.core.events import EventBus
from jarvis.core.interrupt import InterruptFlag
from jarvis.core.memory import TaskMemory
from jarvis.core.orchestrator import Orchestrator
from jarvis.perception import ComputerVision, SimulatedOcr, create_ocr_engine
from jarvis.perception.ocr import NullOcr
from jarvis.security import SecurityPolicy
from jarvis.tools.base import ToolRegistry
from jarvis.tools.builtin import ControllerKit, build_tools
from jarvis.verification import Verifier
from jarvis.voice import ConsoleSpeaker


@dataclass
class Assistant:
    """Fully wired JARVIS instance."""

    settings: Settings
    events: EventBus
    interrupt: InterruptFlag
    backend: object
    vision: ComputerVision
    mouse: MouseController
    keyboard: KeyboardController
    windows: WindowController
    launcher: AppLauncher
    filesystem: FilesystemController
    terminal: TerminalRunner
    tools: ToolRegistry
    security: SecurityPolicy
    verifier: Verifier
    memory: TaskMemory
    brain: RuleBasedBrain
    speaker: ConsoleSpeaker
    orchestrator: Orchestrator


def build_assistant(
    settings: Settings,
    *,
    events: EventBus | None = None,
    security_policy: SecurityPolicy | None = None,
) -> Assistant:
    """Build the whole object graph. Pure - no side effects beyond dirs."""
    settings.ensure_dirs()
    events = events or EventBus()
    interrupt = InterruptFlag()

    backend = create_backend(settings.backend, settings, events)

    # Perception: the simulated backend carries its own text; real screens
    # need OCR (tesseract when installed, otherwise checks report UNKNOWN).
    from jarvis.control.backends import SimulatedBackend

    if isinstance(backend, SimulatedBackend):
        ocr = SimulatedOcr()
    else:
        ocr = create_ocr_engine()
        if isinstance(ocr, NullOcr):
            events.emit(
                "activity",
                "OCR unavailable - install 'jarvis[ocr]' + Tesseract for screen reading",
                level="warning",
            )
    vision = ComputerVision(backend, ocr)

    mouse = MouseController(backend)
    keyboard = KeyboardController(backend, typing_interval=settings.typing_interval)
    windows = WindowController(backend, interrupt)
    launcher = AppLauncher(backend)
    filesystem = FilesystemController(backend)
    terminal = TerminalRunner(settings.allowed_terminal_commands)

    kit = ControllerKit(
        backend=backend,
        mouse=mouse,
        keyboard=keyboard,
        windows=windows,
        launcher=launcher,
        filesystem=filesystem,
        terminal=terminal,
        vision=vision,
        screenshots_dir=settings.screenshots_dir,
    )
    tools: ToolRegistry = build_tools(kit, settings)

    security = security_policy or SecurityPolicy(
        auto_approve_risk=settings.auto_approve_risk,
        events=events,
    )
    verifier = Verifier(backend, vision, interrupt, settings)
    memory = TaskMemory(settings.memory_file)
    brain = RuleBasedBrain()
    speaker = ConsoleSpeaker()

    orchestrator = Orchestrator(
        brain=brain,
        tools=tools,
        security=security,
        verifier=verifier,
        memory=memory,
        events=events,
        interrupt=interrupt,
        settings=settings,
        speaker=speaker,
    )

    return Assistant(
        settings=settings,
        events=events,
        interrupt=interrupt,
        backend=backend,
        vision=vision,
        mouse=mouse,
        keyboard=keyboard,
        windows=windows,
        launcher=launcher,
        filesystem=filesystem,
        terminal=terminal,
        tools=tools,
        security=security,
        verifier=verifier,
        memory=memory,
        brain=brain,
        speaker=speaker,
        orchestrator=orchestrator,
    )


def interactive_approver():
    """Prompt the user on the console for medium/high-risk actions."""

    from jarvis.security import Approver, PermissionRequest

    class ConsoleApprover(Approver):  # noqa: D401 - local on purpose
        def ask(self, request: PermissionRequest) -> bool:
            if not sys.stdin.isatty():
                return False  # non-interactive: stay safe, deny
            try:
                answer = input(
                    f"\n  ⚠ {request.risk.label.upper()} risk: {request.action}\n"
                    f"    Allow? [y/N] "
                )
            except (EOFError, KeyboardInterrupt):
                return False
            return answer.strip().lower() in {"y", "yes"}
    return ConsoleApprover()
