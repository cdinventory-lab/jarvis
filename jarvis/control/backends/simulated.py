"""Simulated backend: a virtual desktop for headless development and tests.

Implements the same contract as the real backend but keeps an in-memory
model: windows with titles/content, processes, mouse position, clicks, typed
text. This makes every computer-control operation independently testable and
lets demos run on machines without a display.

Modelled behaviour (deliberately realistic where it matters):

* launching an app creates a window (after an optional startup latency, so
  wait/verify polling is exercised) and a process,
* clicking inside a window activates it (focus follows click),
* typed text goes into the *active* window's content,
* closing the active window activates the next topmost one,
* `screenshot()` returns a :class:`SimScreenImage` whose text blocks stand in
  for what OCR would extract from a real screenshot.
"""

from __future__ import annotations

import itertools
import time
from collections.abc import Sequence
from dataclasses import dataclass, field

from jarvis.control.backend import (
    BackendError,
    ComputerBackend,
    LaunchHandle,
    WindowInfo,
)

_APP_MENUS = {
    "notepad": ["File  Edit  Format  View  Help"],
    "editor": ["File  Edit  View  Go  Run  Terminal  Help"],
}


@dataclass
class SimWindow:
    """One window on the virtual desktop."""

    id: str
    title: str
    app: str
    process: str
    box: tuple[int, int, int, int]
    content: list[str] = field(default_factory=list)
    minimized: bool = False
    maximized: bool = False
    visible_at: float = 0.0  # monotonic time from which the window exists


@dataclass(frozen=True)
class SimScreenImage:
    """Screenshot stand-in carrying text + geometry a real screenshot has."""

    size: tuple[int, int]
    blocks: tuple[tuple[str, tuple[int, int, int, int]], ...]  # (text, box)


def _window_blocks(window: SimWindow) -> list[tuple[str, tuple[int, int, int, int]]]:
    x, y, w, _h = window.box
    blocks = [(window.title, (x, y, w, 28))]
    line_h = 22
    for i, line in enumerate(window.content):
        blocks.append((line, (x + 12, y + 44 + i * line_h, w - 24, line_h)))
    return blocks


class SimulatedBackend(ComputerBackend):
    """In-memory virtual desktop."""

    name = "simulated"

    def __init__(
        self,
        launch_latency: float = 0.0,
        screen: tuple[int, int] = (1920, 1080),
    ) -> None:
        self._screen = screen
        self._launch_latency = launch_latency
        self._windows: list[SimWindow] = []  # z-order: last = topmost
        self._active_id: str | None = None
        self._processes: set[str] = set()
        self._mouse = (screen[0] // 2, screen[1] // 2)
        self._clipboard = ""
        self._clicks: list[dict[str, object]] = []
        self._keys: list[str] = []
        self._typed_log: list[tuple[str, str]] = []  # (window_id, text)
        self._id_counter = itertools.count(1)

    # ------------------------------------------------------------ introspection

    @property
    def clicks(self) -> list[dict[str, object]]:
        return list(self._clicks)

    @property
    def keys(self) -> list[str]:
        return list(self._keys)

    def window_content(self, title_contains: str) -> list[str]:
        """Content lines of the first window whose title matches."""
        self._materialize()
        for window in reversed(self._windows):
            if title_contains.lower() in window.title.lower():
                return list(window.content)
        return []

    def active_window_title(self) -> str:
        window = self.active_window()
        return window.title if window else ""

    # ------------------------------------------------------------- windows core

    def _materialize(self) -> None:
        """Activate windows whose startup latency has elapsed."""
        now = time.monotonic()
        for window in self._windows:
            if window.visible_at and now >= window.visible_at:
                window.visible_at = 0.0
                self._activate(window)

    def _new_window(
        self,
        title: str,
        app: str,
        process: str,
        content: list[str] | None = None,
        latency: float | None = None,
    ) -> SimWindow:
        index = len([w for w in self._windows if not w.visible_at]) + 1
        offset = 40 + (len(self._windows) % 6) * 34
        window = SimWindow(
            id=f"sim-{next(self._id_counter)}",
            title=title,
            app=app,
            process=process,
            box=(offset, offset + index * 6, 900, 600),
            content=[_APP_MENUS.get(app, ["File  Edit  View  Help"])[:][0]]
            + list(content or [""]),
            visible_at=time.monotonic() + (self._launch_latency if latency is None else latency),
        )
        self._windows.append(window)
        return window

    def _activate(self, window: SimWindow) -> None:
        window.minimized = False
        self._active_id = window.id

    def _find(self, window_id: str | int) -> SimWindow:
        self._materialize()
        for window in self._windows:
            if str(window.id) == str(window_id):
                return window
        raise BackendError(f"no such window: {window_id!r}")

    def _topmost_visible(self) -> SimWindow | None:
        for window in reversed(self._windows):
            if not window.minimized and not window.visible_at:
                return window
        return None

    def _active(self) -> SimWindow | None:
        self._materialize()
        for window in self._windows:
            if window.id == self._active_id and not window.minimized:
                return window
        return None

    # ------------------------------------------------------------------- mouse

    def mouse_position(self) -> tuple[int, int]:
        return self._mouse

    def move_to(self, x: int, y: int, duration: float = 0.0) -> None:
        self._mouse = (int(x), int(y))

    def mouse_down(self, button: str = "left") -> None:
        self._clicks.append({"type": "down", "button": button, "pos": self._mouse})

    def mouse_up(self, button: str = "left") -> None:
        self._clicks.append({"type": "up", "button": button, "pos": self._mouse})

    def click(
        self,
        x: int | None = None,
        y: int | None = None,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.0,
    ) -> None:
        if x is not None and y is not None:
            self._mouse = (int(x), int(y))
        self._materialize()
        self._clicks.append(
            {"type": "click", "pos": self._mouse, "button": button, "clicks": clicks}
        )
        # Focus follows click: activate the topmost window under the cursor.
        mx, my = self._mouse
        for window in reversed(self._windows):
            if window.minimized or window.visible_at:
                continue
            wx, wy, ww, wh = window.box
            if wx <= mx <= wx + ww and wy <= my <= wy + wh:
                self._activate(window)
                break

    def scroll(self, amount: int) -> None:
        self._clicks.append({"type": "scroll", "amount": amount, "pos": self._mouse})

    def drag(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration: float = 0.3,
        button: str = "left",
    ) -> None:
        self._mouse = (int(x1), int(y1))
        self._clicks.append({"type": "drag-start", "pos": self._mouse, "button": button})
        self._mouse = (int(x2), int(y2))
        self._clicks.append({"type": "drag-end", "pos": self._mouse, "button": button})

    # ---------------------------------------------------------------- keyboard

    def key_down(self, key: str) -> None:
        self._keys.append(f"down:{key}")

    def key_up(self, key: str) -> None:
        self._keys.append(f"up:{key}")

    def press_key(self, key: str) -> None:
        self._keys.append(key)
        window = self._active()
        if window is None:
            return
        if key == "enter":
            window.content.append("")
        elif key == "tab":
            window.content[-1] += "    "
        elif key == "backspace":
            if window.content[-1]:
                window.content[-1] = window.content[-1][:-1]

    def hotkey(self, *keys: str) -> None:
        self._keys.append("+".join(keys))
        if [k.lower() for k in keys] == ["ctrl", "v"] and self._clipboard:
            # paste: the focused app receives the clipboard content
            window = self._active()
            if window is not None:
                window.content[-1] += self._clipboard
                self._typed_log.append((window.id, self._clipboard))

    def type_text(self, text: str, interval: float = 0.0) -> None:
        window = self._active()
        if window is None:
            raise BackendError("cannot type: no active window")
        for piece in text.split("\n"):
            window.content[-1] += piece
            if "\n" in text:
                window.content.append("")
        if text.endswith("\n"):
            window.content.append("")
        self._typed_log.append((window.id, text))

    # ------------------------------------------------------------------ screen

    def screenshot(self) -> SimScreenImage:
        self._materialize()
        blocks: list[tuple[str, tuple[int, int, int, int]]] = []
        for window in self._windows:
            if window.minimized or window.visible_at:
                continue
            blocks.extend(_window_blocks(window))
        return SimScreenImage(size=self._screen, blocks=tuple(blocks))

    def screen_size(self) -> tuple[int, int]:
        return self._screen

    # ----------------------------------------------------------------- windows

    def list_windows(self) -> list[WindowInfo]:
        self._materialize()
        return [
            WindowInfo(
                id=window.id,
                title=window.title,
                app=window.app,
                box=window.box,
                active=window.id == self._active_id,
                minimized=window.minimized,
            )
            for window in self._windows
            if not window.visible_at
        ]

    def active_window(self) -> WindowInfo | None:
        self._materialize()
        window = self._active()
        if window is None:
            return None
        return WindowInfo(
            id=window.id,
            title=window.title,
            app=window.app,
            box=window.box,
            active=True,
            minimized=window.minimized,
        )

    def activate_window(self, window_id: str | int) -> None:
        self._activate(self._find(window_id))

    def minimize_window(self, window_id: str | int) -> None:
        window = self._find(window_id)
        window.minimized = True
        if self._active_id == window.id:
            replacement = self._topmost_visible()
            self._active_id = replacement.id if replacement else None

    def maximize_window(self, window_id: str | int) -> None:
        window = self._find(window_id)
        window.minimized = False
        window.maximized = True
        window.box = (0, 0, *self._screen)
        self._activate(window)

    def close_window(self, window_id: str | int) -> None:
        window = self._find(window_id)
        self._windows.remove(window)
        if self._active_id == window.id:
            replacement = self._topmost_visible()
            self._active_id = replacement.id if replacement else None
        # Keep the process around: closing a window does not always exit.

    # ---------------------------------------------------------- OS / processes

    def launch_app(
        self,
        command: Sequence[str],
        *,
        app_name: str = "",
        window_title: str = "",
        process_name: str = "",
        url: str | None = None,
    ) -> LaunchHandle:
        token = app_name or (command[0] if command else "app")
        token = token.lower().removesuffix(".exe").replace("-", " ").replace("_", " ")
        app = token.replace(" ", "")
        display = token.title()
        title = window_title or f"Untitled - {display}"
        process = (process_name or f"{app}.exe").lower()
        self._processes.update({process, app})
        if url:
            title = window_title or f"{url} - {display}"
            content = [url, title]
        else:
            content = [""]
        window = self._new_window(title=title, app=app, process=process, content=content)
        return LaunchHandle(
            pid=10_000 + int(window.id.split("-")[1]),
            command=tuple(command),
            app=app,
            simulated=True,
        )

    def open_path(self, path: str) -> None:
        from pathlib import Path

        target = Path(path).expanduser()
        if not target.exists():
            raise BackendError(f"path does not exist: {target}")
        if target.is_dir():
            self._new_window(
                title=f"{target.name or target}",
                app="explorer",
                process="explorer.exe",
                content=[str(target)],
            )
        else:
            self._new_window(
                title=target.name,
                app="fileviewer",
                process="fileviewer.exe",
                content=[str(target)],
            )

    def open_url(
        self,
        url: str,
        *,
        browser_command: Sequence[str] | None = None,
        title_hint: str = "",
    ) -> None:
        app = "browser"
        if browser_command:
            token = browser_command[0].lower().removesuffix(".exe")
            app = token.replace("-", "").replace("_", "")
        title = title_hint or url
        self._new_window(
            title=title,
            app=app,
            process=f"{app}.exe",
            content=[url, title],
        )

    def process_exists(self, name: str) -> bool:
        needle = name.lower().removesuffix(".exe")
        return any(needle in proc for proc in self._processes)

    def list_processes(self) -> list[str]:
        return sorted(self._processes)

    # --------------------------------------------------------------- clipboard

    def clipboard_get(self) -> str:
        return self._clipboard

    def clipboard_set(self, text: str) -> None:
        self._clipboard = text
