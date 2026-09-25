"""Real computer control via PyAutoGUI (+ pygetwindow / psutil / pyperclip).

This is the backend that runs on the user's PC (Windows recommended).
All heavy dependencies are imported lazily so the rest of JARVIS - and its
test suite - runs on machines without a display.

Windows notes:
* window operations use `pygetwindow` (installed with PyAutoGUI on Windows),
* app resolution (PATH / App Paths registry / common install locations)
  happens in :mod:`jarvis.control.apps`; this backend just executes,
* `os.startfile` is used as a fallback for registered apps, URLs and files.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import webbrowser
from collections.abc import Sequence
from urllib.parse import urlparse

from jarvis.control.backend import (
    BackendError,
    BackendUnavailableError,
    ComputerBackend,
    LaunchHandle,
    WindowInfo,
)

_INSTALL_HINT = (
    "pip install 'jarvis[computer]'. On Linux/X11 a DISPLAY is required; "
    "Wayland users need XWayland (PyAutoGUI is X11-only)."
)


class PyAutoGuiBackend(ComputerBackend):
    """Mouse, keyboard, screenshots and (on Windows) window management."""

    name = "pyautogui"

    def __init__(self) -> None:
        try:
            import pyautogui  # noqa: PLC0415 - deliberate lazy import
        except Exception as exc:  # pragma: no cover - depends on host machine
            raise BackendUnavailableError(
                f"PyAutoGUI is not usable on this machine ({exc}). {_INSTALL_HINT}"
            ) from exc
        self._pyautogui = pyautogui
        self._pyautogui.FAILSAFE = True  # slam mouse to a corner to abort

        # Probing the screen size fails on headless machines - detect early.
        try:
            self._pyautogui.size()
        except Exception as exc:  # pragma: no cover - depends on host machine
            raise BackendUnavailableError(
                f"No usable display for PyAutoGUI ({exc}). {_INSTALL_HINT}"
            ) from exc

        self._pygetwindow = None
        if sys.platform == "win32":
            try:
                import pygetwindow  # noqa: PLC0415
                self._pygetwindow = pygetwindow
            except Exception as exc:  # pragma: no cover
                raise BackendUnavailableError(
                    f"pygetwindow unavailable ({exc}); window control needs Windows."
                ) from exc
        self._window_cache: dict[str, object] = {}

    # ------------------------------------------------------------------- mouse

    def mouse_position(self) -> tuple[int, int]:
        x, y = self._pyautogui.position()
        return int(x), int(y)

    def move_to(self, x: int, y: int, duration: float = 0.0) -> None:
        self._pyautogui.moveTo(int(x), int(y), duration=duration)

    def mouse_down(self, button: str = "left") -> None:
        self._pyautogui.mouseDown(button=button)

    def mouse_up(self, button: str = "left") -> None:
        self._pyautogui.mouseUp(button=button)

    def click(
        self,
        x: int | None = None,
        y: int | None = None,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.0,
    ) -> None:
        self._pyautogui.click(
            x=None if x is None else int(x),
            y=None if y is None else int(y),
            clicks=clicks,
            interval=interval,
            button=button,
        )

    def scroll(self, amount: int) -> None:
        self._pyautogui.scroll(int(amount))

    def drag(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration: float = 0.3,
        button: str = "left",
    ) -> None:
        self._pyautogui.moveTo(int(x1), int(y1))
        self._pyautogui.dragTo(int(x2), int(y2), duration=duration, button=button)

    # ---------------------------------------------------------------- keyboard

    def key_down(self, key: str) -> None:
        self._pyautogui.keyDown(key)

    def key_up(self, key: str) -> None:
        self._pyautogui.keyUp(key)

    def press_key(self, key: str) -> None:
        self._pyautogui.press(key)

    def hotkey(self, *keys: str) -> None:
        self._pyautogui.hotkey(*keys)

    def type_text(self, text: str, interval: float = 0.0) -> None:
        self._pyautogui.write(text, interval=interval)

    # ------------------------------------------------------------------ screen

    def screenshot(self) -> object:
        """PIL Image of the screen (fed to the OCR engine)."""
        return self._pyautogui.screenshot()

    def screen_size(self) -> tuple[int, int]:
        w, h = self._pyautogui.size()
        return int(w), int(h)

    # ----------------------------------------------------------------- windows

    def _require_window_support(self):
        if self._pygetwindow is None:
            raise BackendUnavailableError(
                "window management is currently supported on Windows only "
                "(pygetwindow); mouse/keyboard/screen still work everywhere."
            )
        return self._pygetwindow

    def list_windows(self) -> list[WindowInfo]:
        gw = self._require_window_support()
        self._window_cache.clear()
        result: list[WindowInfo] = []
        for window in gw.getAllWindows():
            if not window.title.strip():
                continue
            window_id = str(getattr(window, "_hWnd", id(window)))
            self._window_cache[window_id] = window
            result.append(
                WindowInfo(
                    id=window_id,
                    title=window.title,
                    app="",  # best effort: real app name comes from the process
                    box=(int(window.left), int(window.top), int(window.width), int(window.height)),
                    active=bool(window.isActive),
                    minimized=bool(window.isMinimized),
                )
            )
        return result

    def active_window(self) -> WindowInfo | None:
        for window in self.list_windows():
            if window.active:
                return window
        return None

    def _get_window_object(self, window_id: str | int):
        if str(window_id) not in self._window_cache:
            self.list_windows()  # refresh cache
        window = self._window_cache.get(str(window_id))
        if window is None:
            raise BackendError(f"no such window: {window_id!r}")
        return window

    def activate_window(self, window_id: str | int) -> None:
        self._get_window_object(window_id).activate()

    def minimize_window(self, window_id: str | int) -> None:
        self._get_window_object(window_id).minimize()

    def maximize_window(self, window_id: str | int) -> None:
        self._get_window_object(window_id).maximize()

    def close_window(self, window_id: str | int) -> None:
        self._get_window_object(window_id).close()

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
        cmd = [str(part) for part in command]
        if url:
            cmd.append(url)
        if not cmd:
            raise BackendError("launch_app needs a command or a url")

        # Single-token "commands" (e.g. 'notepad.exe', a URL, a document) can
        # go through the OS shell handler - the safest option on Windows.
        if len(cmd) == 1:
            token = cmd[0]
            looks_like_path = os.sep in token or token.startswith(".")
            on_path = shutil.which(token)
            if not on_path and not looks_like_path and not os.path.isabs(token):
                try:
                    if os.name == "nt":
                        os.startfile(token)  # noqa: S606 - registered apps only
                        return LaunchHandle(None, tuple(cmd), app_name or token)
                    webbrowser.open(token)
                    return LaunchHandle(None, tuple(cmd), app_name or token)
                except OSError as exc:
                    raise BackendError(f"could not start {token!r}: {exc}") from exc

        try:
            process = subprocess.Popen(  # noqa: S603 - command resolved by AppLauncher
                cmd,
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
        except FileNotFoundError as exc:
            raise BackendError(f"executable not found: {cmd[0]!r}") from exc
        except OSError as exc:
            raise BackendError(f"could not start {cmd[0]!r}: {exc}") from exc
        return LaunchHandle(pid=process.pid, command=tuple(cmd), app=app_name or cmd[0])

    def open_path(self, path: str) -> None:
        target = os.path.expanduser(path)
        if not os.path.exists(target):
            raise BackendError(f"path does not exist: {target}")
        try:
            if os.name == "nt":
                os.startfile(target)  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", target])  # noqa: S603
            else:
                subprocess.Popen(["xdg-open", target])  # noqa: S603
        except OSError as exc:
            raise BackendError(f"could not open {target!r}: {exc}") from exc

    def open_url(
        self,
        url: str,
        *,
        browser_command: Sequence[str] | None = None,
        title_hint: str = "",
    ) -> None:
        if not urlparse(url).scheme:
            url = "https://" + url
        if browser_command:
            self.launch_app(list(browser_command), app_name="browser", url=url)
            return
        if not webbrowser.open(url):
            raise BackendError(f"no web browser available for {url}")

    def process_exists(self, name: str) -> bool:
        needle = name.lower().removesuffix(".exe")
        try:
            import psutil  # noqa: PLC0415

            for process in psutil.process_iter(["name"]):
                pname = (process.info.get("name") or "").lower()
                if pname and pname.removesuffix(".exe") == needle:
                    return True
            return False
        except ImportError:
            return needle in (proc.lower() for proc in self.list_processes())

    def list_processes(self) -> list[str]:
        try:
            import psutil  # noqa: PLC0415

            names = {p.info.get("name") for p in psutil.process_iter(["name"])}
            return sorted(n for n in names if n)
        except ImportError:
            pass
        try:
            if os.name == "nt":
                output = subprocess.run(  # noqa: S603 - fixed command
                    ["tasklist", "/FO", "CSV", "/NH"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=True,
                ).stdout
                return sorted(
                    {line.split('","')[0].strip('"') for line in output.splitlines() if line}
                )
            output = subprocess.run(  # noqa: S603 - fixed command
                ["ps", "-e", "-o", "comm="],
                capture_output=True,
                text=True,
                timeout=15,
                check=True,
            ).stdout
            return sorted({line.strip() for line in output.splitlines() if line.strip()})
        except (OSError, subprocess.SubprocessError) as exc:
            raise BackendError(f"could not list processes: {exc}") from exc

    # --------------------------------------------------------------- clipboard

    @staticmethod
    def _pyperclip():
        try:
            import pyperclip  # noqa: PLC0415

            return pyperclip
        except ImportError as exc:
            raise BackendUnavailableError(
                f"pyperclip is required for clipboard support ({exc}). {_INSTALL_HINT}"
            ) from exc

    def clipboard_get(self) -> str:
        return self._pyperclip().paste()

    def clipboard_set(self, text: str) -> None:
        self._pyperclip().copy(text)
