"""Window controller (spec section 8: windows/OS control).

Find, focus, inspect, minimise/maximise and close windows - always by
re-querying the backend, never by cached coordinates, so UI movement is
tolerated.
"""

from __future__ import annotations

import logging

from jarvis.control.backend import BackendError, ComputerBackend, WindowInfo
from jarvis.core.interrupt import InterruptFlag

logger = logging.getLogger("jarvis.windows")


class WindowError(RuntimeError):
    """Window operation failed."""


class WindowController:
    def __init__(self, backend: ComputerBackend, interrupt: InterruptFlag) -> None:
        self.backend = backend
        self.interrupt = interrupt

    # ------------------------------------------------------------------ queries

    def windows(self) -> list[WindowInfo]:
        """All visible windows, refreshed from the backend."""
        return self.backend.list_windows()

    def active(self) -> WindowInfo | None:
        return self.backend.active_window()

    def find(
        self,
        title_contains: str | None = None,
        app: str | None = None,
    ) -> WindowInfo | None:
        """Best-matching window: prefer the active one, else newest match."""
        windows = self.windows()
        matches = [w for w in windows if w.matches(title_contains, app)]
        if not matches:
            return None
        for window in matches:
            if window.active:
                return window
        return matches[-1]

    def find_all(
        self,
        title_contains: str | None = None,
        app: str | None = None,
    ) -> list[WindowInfo]:
        return [w for w in self.windows() if w.matches(title_contains, app)]

    def wait_for(
        self,
        title_contains: str | None = None,
        app: str | None = None,
        timeout: float = 10.0,
    ) -> WindowInfo | None:
        """Poll until a matching window exists (interruptible)."""
        found: WindowInfo | None = None

        def _predicate() -> bool:
            nonlocal found
            found = self.find(title_contains, app)
            return found is not None

        InterruptFlag.wait_until(_predicate, timeout, self.interrupt)
        return found

    # ----------------------------------------------------------------- actions

    def activate(self, window: WindowInfo | int | str) -> WindowInfo:
        """Bring a window to the foreground."""
        window_id = window.id if isinstance(window, WindowInfo) else window
        try:
            self.backend.activate_window(window_id)
        except BackendError as exc:
            raise WindowError(f"could not activate window {window_id!r}: {exc}") from exc
        return self.find() or self.active() or WindowInfo(
            id=window_id, title="", app="", box=(0, 0, 0, 0), active=True
        )

    def focus_app(self, title_contains: str | None = None, app: str | None = None) -> WindowInfo:
        window = self.find(title_contains, app)
        if window is None:
            raise WindowError(
                f"no window matching title~{title_contains!r}/app~{app!r} is open"
            )
        return self.activate(window)

    def minimize(self, window: WindowInfo | int | str) -> None:
        window_id = window.id if isinstance(window, WindowInfo) else window
        self.backend.minimize_window(window_id)

    def maximize(self, window: WindowInfo | int | str) -> None:
        window_id = window.id if isinstance(window, WindowInfo) else window
        self.backend.maximize_window(window_id)

    def close(self, window: WindowInfo | int | str) -> None:
        window_id = window.id if isinstance(window, WindowInfo) else window
        try:
            self.backend.close_window(window_id)
        except BackendError as exc:
            raise WindowError(f"could not close window {window_id!r}: {exc}") from exc

    def close_app(
        self,
        title_contains: str | None = None,
        app: str | None = None,
    ) -> int:
        """Close every window matching the hints. Returns count closed."""
        matches = self.find_all(title_contains, app)
        for window in matches:
            self.close(window)
            logger.debug("closed window %r", window.title)
        return len(matches)

    def wait_until_closed(
        self,
        title_contains: str | None = None,
        app: str | None = None,
        timeout: float = 10.0,
    ) -> bool:
        def _gone() -> bool:
            return not self.find_all(title_contains, app)

        return InterruptFlag.wait_until(_gone, timeout, self.interrupt)
