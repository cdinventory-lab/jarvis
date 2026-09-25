"""Computer-backend abstraction (the platform seam).

Everything above this file is platform-agnostic. Two backends exist today:

* :class:`jarvis.control.backends.simulated.SimulatedBackend` - a virtual
  desktop with windows, processes, typing and clicks. Lets the whole agent
  (and its test suite) run on headless machines and CI.
* :class:`jarvis.control.backends.pyautogui_backend.PyAutoGuiBackend` - real
  mouse/keyboard/screenshot control via PyAutoGUI (+ pygetwindow on Windows,
  psutil for processes). This is what runs on the user's PC.

Adding a backend (e.g. a remote VNC/VM backend) means implementing this
interface - nothing else in JARVIS changes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

#: Mouse buttons.
BUTTONS = ("left", "middle", "right")


@dataclass(frozen=True)
class WindowInfo:
    """A visible window, as reported by the backend."""

    id: str | int
    title: str
    app: str
    box: tuple[int, int, int, int]  # x, y, width, height
    active: bool = False
    minimized: bool = False

    @property
    def center(self) -> tuple[int, int]:
        x, y, w, h = self.box
        return (x + w // 2, y + h // 2)

    def matches(self, title_contains: str | None = None, app: str | None = None) -> bool:
        """True if this window matches the given (case-insensitive) hints."""
        if title_contains:
            if title_contains.lower() not in self.title.lower():
                return False
        if app:
            if app.lower() not in (self.app.lower(), self.title.lower()):
                return False
        return title_contains is not None or app is not None


@dataclass(frozen=True)
class LaunchHandle:
    """Result of launching an app/process."""

    pid: int | None
    command: tuple[str, ...]
    app: str
    simulated: bool = False


class BackendError(RuntimeError):
    """A backend operation failed."""


class BackendUnavailableError(BackendError):
    """The backend itself cannot start (missing dependency / no display)."""


class ComputerBackend(ABC):
    """Low-level computer control operations.

    Concrete backends translate these into platform calls. Methods raise
    :class:`BackendError` on failure; callers (tools/verifier) handle that.
    """

    #: Backend name shown in the UI ("simulated", "pyautogui", ...).
    name: str = "abstract"

    # ------------------------------------------------------------------ mouse

    @abstractmethod
    def mouse_position(self) -> tuple[int, int]: ...

    @abstractmethod
    def move_to(self, x: int, y: int, duration: float = 0.0) -> None: ...

    @abstractmethod
    def mouse_down(self, button: str = "left") -> None: ...

    @abstractmethod
    def mouse_up(self, button: str = "left") -> None: ...

    @abstractmethod
    def click(
        self,
        x: int | None = None,
        y: int | None = None,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.0,
    ) -> None: ...

    @abstractmethod
    def scroll(self, amount: int) -> None: ...

    @abstractmethod
    def drag(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration: float = 0.3,
        button: str = "left",
    ) -> None: ...

    # --------------------------------------------------------------- keyboard

    @abstractmethod
    def key_down(self, key: str) -> None: ...

    @abstractmethod
    def key_up(self, key: str) -> None: ...

    @abstractmethod
    def press_key(self, key: str) -> None: ...

    @abstractmethod
    def hotkey(self, *keys: str) -> None: ...

    @abstractmethod
    def type_text(self, text: str, interval: float = 0.0) -> None: ...

    # ----------------------------------------------------------------- screen

    @abstractmethod
    def screenshot(self) -> object:
        """Capture the screen. Returns a backend-specific image object."""

    @abstractmethod
    def screen_size(self) -> tuple[int, int]: ...

    # ---------------------------------------------------------------- windows

    @abstractmethod
    def list_windows(self) -> list[WindowInfo]: ...

    @abstractmethod
    def active_window(self) -> WindowInfo | None: ...

    @abstractmethod
    def activate_window(self, window_id: str | int) -> None: ...

    @abstractmethod
    def minimize_window(self, window_id: str | int) -> None: ...

    @abstractmethod
    def maximize_window(self, window_id: str | int) -> None: ...

    @abstractmethod
    def close_window(self, window_id: str | int) -> None: ...

    # ------------------------------------------------------- OS / processes

    def launch_app(
        self,
        command: Sequence[str],
        *,
        app_name: str = "",
        window_title: str = "",
        process_name: str = "",
        url: str | None = None,
    ) -> LaunchHandle:
        """Start an application.

        `app_name` / `window_title` / `process_name` are metadata hints: the
        simulated backend uses them to create a realistic window, real
        backends use them for logging. `url` (when given) is appended as the
        app argument (e.g. opening a browser at a URL).
        """
        raise NotImplementedError

    def open_path(self, path: str) -> None:
        """Open a file/folder with the OS default handler."""
        raise NotImplementedError

    def open_url(
        self,
        url: str,
        *,
        browser_command: Sequence[str] | None = None,
        title_hint: str = "",
    ) -> None:
        """Open a URL (optionally in a specific browser)."""
        raise NotImplementedError

    @abstractmethod
    def process_exists(self, name: str) -> bool: ...

    @abstractmethod
    def list_processes(self) -> list[str]: ...

    # -------------------------------------------------------------- clipboard

    def clipboard_get(self) -> str:
        raise BackendError(f"backend {self.name} does not support the clipboard")

    def clipboard_set(self, text: str) -> None:
        raise BackendError(f"backend {self.name} does not support the clipboard")
