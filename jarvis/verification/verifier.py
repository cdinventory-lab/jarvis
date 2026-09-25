"""Verification system (spec section 12).

JARVIS never assumes an action succeeded just because the command was sent.
Every step carries an :class:`~jarvis.core.planner.models.Expectation`; the
verifier re-observes the world (windows, processes, filesystem, screen text)
and reports SUCCESS / FAILED / UNKNOWN / NEEDS_USER.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from jarvis.control.backend import ComputerBackend, WindowInfo
from jarvis.control.windows import WindowController
from jarvis.core.interrupt import InterruptFlag
from jarvis.core.planner.models import Expectation, ExpectationKind
from jarvis.perception.screenshot.service import ComputerVision

if TYPE_CHECKING:
    from jarvis.config.settings import Settings

logger = logging.getLogger("jarvis.verification")


class VerificationStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    UNKNOWN = "unknown"      # could not observe (e.g. no OCR installed)
    NEEDS_USER = "needs_user"  # cannot verify + strict mode: ask the human


@dataclass(frozen=True)
class VerificationResult:
    status: VerificationStatus
    detail: str
    evidence: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == VerificationStatus.SUCCESS


class Verifier:
    """Checks expectations against the observed world."""

    def __init__(
        self,
        backend: ComputerBackend,
        vision: ComputerVision | None,
        interrupt: InterruptFlag,
        settings: Settings,
    ) -> None:
        self.backend = backend
        self.vision = vision
        self.interrupt = interrupt
        self.settings = settings
        self._windows = WindowController(backend, interrupt)

    def verify(self, expectation: Expectation, timeout: float | None = None) -> VerificationResult:
        """Poll the world until the expectation holds, fails, or times out."""
        if expectation.kind == ExpectationKind.NONE:
            return VerificationResult(VerificationStatus.UNKNOWN, "no expectation defined")
        timeout = self.settings.verify_timeout if timeout is None else timeout
        check = self._checker_for(expectation)
        if check is None:
            return VerificationResult(
                VerificationStatus.NEEDS_USER,
                f"cannot verify expectation {expectation.kind.value} yet",
            )
        deadline = time.monotonic() + max(0.0, timeout)
        last_detail = ""
        while True:
            if self.interrupt.stopped:
                return VerificationResult(VerificationStatus.FAILED, "interrupted")
            ok, detail, evidence = check()
            last_detail = detail
            if ok:
                return VerificationResult(VerificationStatus.SUCCESS, detail, evidence)
            if self.interrupt.stopped:
                return VerificationResult(VerificationStatus.FAILED, "interrupted", evidence)
            if time.monotonic() >= deadline:
                break
            self.interrupt.sleep(0.2)

        # Distinguish *verified failure* from *unable to observe*.
        if last_detail.startswith("UNVERIFIABLE:"):
            status = (
                VerificationStatus.NEEDS_USER
                if self.settings.verify_strict
                else VerificationStatus.UNKNOWN
            )
            return VerificationResult(status, last_detail.removeprefix("UNVERIFIABLE: "))
        return VerificationResult(VerificationStatus.FAILED, last_detail)

    # ------------------------------------------------------------------ checkers

    def _checker_for(self, expectation: Expectation):
        kind = expectation.kind
        params = dict(expectation.params)

        if kind == ExpectationKind.WINDOW_APPEARS:
            return lambda: self._check_window(params, want_visible=True)
        if kind == ExpectationKind.WINDOW_CLOSED:
            return lambda: self._check_window(params, want_visible=False)
        if kind == ExpectationKind.ACTIVE_WINDOW:
            return lambda: self._check_active_window(params)
        if kind == ExpectationKind.PROCESS_RUNNING:
            name = str(params.get("name", ""))

            def _process() -> tuple[bool, str, dict]:
                running = self.backend.process_exists(name)
                if running:
                    return True, f"process '{name}' running", {"name": name}
                return False, f"process '{name}' not detected", {"name": name}

            return _process
        if kind == ExpectationKind.FILE_EXISTS:
            path = str(params.get("path", ""))

            def _file() -> tuple[bool, str, dict]:
                if os.path.isfile(path):
                    return True, f"file exists: {path}", {"path": path}
                return False, f"file not found: {path}", {"path": path}

            return _file
        if kind == ExpectationKind.DIR_EXISTS:
            path = str(params.get("path", ""))

            def _dir() -> tuple[bool, str, dict]:
                if os.path.isdir(path):
                    return True, f"folder exists: {path}", {"path": path}
                return False, f"folder not found: {path}", {"path": path}

            return _dir
        if kind == ExpectationKind.SCREEN_CONTAINS_TEXT:
            text = str(params.get("text", ""))
            return lambda: self._check_screen_text(text)
        return None

    # ------------------------------------------------------------------ helpers

    def _match_windows(
        self, title: str | None, app: str | None, extra_titles: list[str]
    ) -> list[WindowInfo]:
        matches: list[WindowInfo] = []
        for window in self.backend.list_windows():
            if window.matches(title, app) or any(window.matches(t) for t in extra_titles):
                matches.append(window)
        return matches

    def _check_window(self, params: dict, want_visible: bool) -> tuple[bool, str, dict]:
        title = params.get("title_contains")
        app = params.get("app")
        titles = list(params.get("any_title_contains") or [])
        matches = self._match_windows(title, app, titles)
        label = title or app or (titles[0] if titles else "?")
        if want_visible:
            if matches:
                return True, f"window detected: {matches[0].title!r}", {"title": matches[0].title}
            return False, f"no window matching {label!r} is open", {"hint": label}
        if matches:
            return False, f"window still open: {matches[0].title!r}", {"title": matches[0].title}
        return True, f"window {label!r} is closed", {"hint": label}

    def _check_active_window(self, params: dict) -> tuple[bool, str, dict]:
        active = self.backend.active_window()
        if active is None:
            return False, "no active window", {}
        title = params.get("title_contains")
        app = params.get("app")
        titles = list(params.get("any_title_contains") or [])
        if active.matches(title, app) or any(active.matches(t) for t in titles):
            return True, f"active window: {active.title!r}", {"title": active.title}
        label = title or app or (titles[0] if titles else "?")
        return False, f"active window is {active.title!r}, expected {label!r}", {
            "active": active.title,
        }

    def _check_screen_text(self, text: str) -> tuple[bool, str, dict]:
        if self.vision is None or not getattr(self.vision.ocr, "available", False):
            return (
                False,
                f"UNVERIFIABLE: cannot read the screen (no OCR available) to confirm {text!r}",
                {},
            )
        analysis = self.vision.analyze_screen()
        if analysis.contains_text(text):
            return True, f"text {text!r} found on screen", {"found": text}
        return False, f"text {text!r} not visible on screen", {}
