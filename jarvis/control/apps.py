"""Application launching (spec sections 8 and 10).

`APP_REGISTRY` knows how to find common applications on Windows (PATH,
App Paths registry, default install locations) and on Linux/macOS for
development. Unknown apps fall back to a generic PATH lookup, which is a
medium-risk action - never a blind shell execution.
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from jarvis.control.backend import BackendError, ComputerBackend, LaunchHandle
from jarvis.security.permissions import RiskLevel

logger = logging.getLogger("jarvis.apps")


class AppLaunchError(RuntimeError):
    """Could not resolve or start the requested application."""


@dataclass(frozen=True)
class AppSpec:
    """How to launch and recognise one application."""

    name: str
    display: str
    aliases: tuple[str, ...]
    windows: tuple[str, ...] = ()
    windows_paths: tuple[str, ...] = ()
    linux: tuple[str, ...] = ()
    macos: tuple[str, ...] = ()
    window_titles: tuple[str, ...] = ()  # substrings expected in the title
    process_names: tuple[str, ...] = ()
    is_browser: bool = False
    risk: RiskLevel = RiskLevel.LOW


def _spec(
    name: str,
    display: str,
    aliases: Sequence[str],
    windows: Sequence[str] = (),
    windows_paths: Sequence[str] = (),
    linux: Sequence[str] = (),
    macos: Sequence[str] = (),
    titles: Sequence[str] = (),
    processes: Sequence[str] = (),
    browser: bool = False,
) -> AppSpec:
    return AppSpec(
        name=name,
        display=display,
        aliases=tuple(aliases),
        windows=tuple(windows),
        windows_paths=tuple(windows_paths),
        linux=tuple(linux),
        macos=tuple(macos),
        window_titles=tuple(titles),
        process_names=tuple(processes),
        is_browser=browser,
    )


APP_REGISTRY: dict[str, AppSpec] = {
    spec.name: spec
    for spec in (
        _spec("notepad", "Notepad", ("notepad", "note pad", "text editor"),
              windows=("notepad.exe",), linux=("gedit", "mousepad", "kate", "xed"),
              macos=("open", "-a", "TextEdit"), titles=("Notepad",),
              processes=("notepad.exe", "notepad")),
        _spec("chrome", "Google Chrome",
              ("chrome", "google chrome", "google", "chromium"),
              windows=("chrome.exe",),
              windows_paths=(
                  r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
                  r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
                  r"%LocalAppData%\Google\Chrome\Application\chrome.exe",
              ),
              linux=("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"),
              macos=("open", "-a", "Google Chrome"), titles=("Chrome",),
              processes=("chrome.exe", "chrome"), browser=True),
        _spec("edge", "Microsoft Edge", ("edge", "microsoft edge", "msedge"),
              windows=("msedge.exe",),
              windows_paths=(
                  r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
                  r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
              ),
              linux=("microsoft-edge", "microsoft-edge-stable"),
              titles=("Edge",), processes=("msedge.exe", "msedge"), browser=True),
        _spec("firefox", "Mozilla Firefox", ("firefox", "mozilla firefox"),
              windows=("firefox.exe",), linux=("firefox",),
              macos=("open", "-a", "Firefox"), titles=("Firefox",),
              processes=("firefox.exe", "firefox"), browser=True),
        _spec("blender", "Blender", ("blender", "blender 3d"),
              windows=("blender.exe", "blender-launcher.exe"), linux=("blender",),
              macos=("open", "-a", "Blender"), titles=("Blender",),
              processes=("blender.exe", "blender")),
        _spec("vscode", "Visual Studio Code",
              ("vscode", "vs code", "visual studio code", "code", "visual code"),
              windows=("code", "code.cmd"),
              windows_paths=(r"%LocalAppData%\Programs\Microsoft VS Code\Code.exe",),
              linux=("code", "code-oss"), macos=("open", "-a", "Visual Studio Code"),
              titles=("Visual Studio Code", "VS Code"), processes=("code.exe", "code")),
        _spec("explorer", "File Explorer",
              ("explorer", "file explorer", "files", "windows explorer", "folder explorer"),
              windows=("explorer.exe",), titles=("File Explorer", "Explorer"),
              processes=("explorer.exe",)),
        _spec("terminal", "Terminal",
              ("terminal", "cmd", "command prompt", "powershell", "windows terminal",
               "console", "shell"),
              windows=("wt.exe", "cmd.exe"),
              linux=("x-terminal-emulator", "gnome-terminal", "konsole", "xterm"),
              macos=("open", "-a", "Terminal"),
              titles=("Terminal", "Command Prompt", "PowerShell"),
              processes=("wt.exe", "cmd.exe", "WindowsTerminal.exe")),
        _spec("calculator", "Calculator", ("calculator", "calc"),
              windows=("calc.exe",), titles=("Calculator",), processes=("calc.exe",)),
        _spec("paint", "Paint", ("paint", "mspaint", "ms paint", "paintbrush"),
              windows=("mspaint.exe",), titles=("Paint",), processes=("mspaint.exe",)),
        _spec("word", "Microsoft Word", ("word", "microsoft word", "ms word"),
              windows=("winword.exe",), titles=("- Word", "Word"),
              processes=("winword.exe",)),
        _spec("excel", "Microsoft Excel", ("excel", "microsoft excel", "ms excel"),
              windows=("excel.exe",), titles=("- Excel", "Excel"), processes=("excel.exe",)),
        _spec("powerpoint", "Microsoft PowerPoint",
              ("powerpoint", "microsoft powerpoint", "ms powerpoint"),
              windows=("powerpnt.exe",), titles=("PowerPoint",),
              processes=("powerpnt.exe",)),
    )
}

# alias (lowercase) -> canonical name
_ALIAS_INDEX: dict[str, str] = {
    alias: spec.name for spec in APP_REGISTRY.values() for alias in spec.aliases
}
_ALIAS_INDEX.update({spec.name: spec.name for spec in APP_REGISTRY.values()})

#: Well-known user folders, openable by name (spec: "Open my Downloads folder").
USER_FOLDERS: dict[str, str] = {
    "downloads": "Downloads",
    "documents": "Documents",
    "desktop": "Desktop",
    "pictures": "Pictures",
    "videos": "Videos",
    "music": "Music",
    "home": "",
}


def resolve_app_name(text: str) -> AppSpec | None:
    """Map free text ("vs code", "Google Chrome") to an AppSpec, or None."""
    cleaned = text.strip().lower().strip(".,!?")
    if not cleaned:
        return None
    if cleaned in _ALIAS_INDEX:
        return APP_REGISTRY[_ALIAS_INDEX[cleaned]]
    # tolerate small wording differences: "the notepad", "chrome browser"
    cleaned = (
        cleaned.removeprefix("the ").removesuffix(" browser").removesuffix(" app")
        .removesuffix(" application").removesuffix(" program").strip()
    )
    if cleaned in _ALIAS_INDEX:
        return APP_REGISTRY[_ALIAS_INDEX[cleaned]]
    import difflib

    close = difflib.get_close_matches(cleaned, _ALIAS_INDEX.keys(), n=1, cutoff=0.8)
    if close:
        return APP_REGISTRY[_ALIAS_INDEX[close[0]]]
    return None


def _windows_app_paths_lookup(exe: str) -> str | None:
    """Look the executable up in HKLM\\...\\App Paths (Windows only)."""
    if sys.platform != "win32":
        return None
    import winreg  # noqa: PLC0415 - Windows only

    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(
                root, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe}"
            ) as key:
                value, _ = winreg.QueryValueEx(key, None)
                if value and os.path.exists(value):
                    return value
        except OSError:
            continue
    return None


class AppLauncher:
    """Resolves app names to concrete commands and starts them via a backend."""

    def __init__(self, backend: ComputerBackend, platform: str | None = None) -> None:
        self.backend = backend
        self.platform = platform or sys.platform

    # ------------------------------------------------------------- resolution

    def resolve_command(self, spec: AppSpec) -> tuple[str, ...] | None:
        """First launch command for this spec that actually exists locally."""
        candidates: Sequence[str]
        if self.platform.startswith("win"):
            candidates = spec.windows
            for token in candidates:
                found = shutil.which(token)
                if found:
                    return (found,)
                exe = token if token.lower().endswith(".exe") else f"{token}.exe"
                from_registry = _windows_app_paths_lookup(exe)
                if from_registry:
                    return (from_registry,)
                for template in spec.windows_paths:
                    path = Path(os.path.expandvars(template))
                    if path.is_file():
                        return (str(path),)
        elif self.platform == "darwin":
            candidates = []
            for entry in (spec.macos, spec.linux):
                candidates.extend(entry)
        else:
            candidates = spec.linux
            for token in candidates:
                found = shutil.which(token)
                if found:
                    return (found,)
        if not candidates:
            return None
        return (candidates[0],)  # last resort: let the backend/OS resolve it

    def generic_command(self, name: str) -> tuple[str, ...] | None:
        """Try to resolve an unknown app name from PATH. Returns None if absent."""
        token = name.strip().lower()
        for variant in (token, f"{token}.exe"):
            found = shutil.which(variant)
            if found:
                return (found,)
        return None

    # --------------------------------------------------------------- launching

    def launch(
        self,
        spec: AppSpec,
        url: str | None = None,
        title_hint: str = "",
    ) -> LaunchHandle:
        """Start a registered application (optionally at a URL).

        `title_hint` describes the page opened at `url` ("query - Search"),
        which the simulated backend uses as the window title.
        """
        command = self.resolve_command(spec)
        if command is None:
            # Let the backend try the OS shell handler (os.startfile & co).
            command = (spec.windows[0] if spec.windows else spec.name,)
        try:
            handle = self.backend.launch_app(
                command,
                app_name=spec.name,
                window_title=title_hint
                or (spec.window_titles[0] if spec.window_titles else spec.display),
                process_name=spec.process_names[0] if spec.process_names else spec.name,
                url=url,
            )
        except BackendError as exc:
            raise AppLaunchError(f"could not start {spec.display}: {exc}") from exc
        logger.info("launched %s via %s", spec.display, " ".join(handle.command))
        return handle

    def launch_by_name(self, name: str, url: str | None = None) -> tuple[LaunchHandle, AppSpec | None]:
        """Launch by free text. Unknown names get a generic PATH lookup.

        Returns (handle, spec) - spec is None when the app was not registered
        (which makes the action medium-risk, enforced by the tool layer).
        """
        spec = resolve_app_name(name)
        if spec is not None:
            return self.launch(spec, url=url), spec
        command = self.generic_command(name)
        try:
            if command is not None:
                handle = self.backend.launch_app(
                    command, app_name=name, window_title=name.title()
                )
            else:
                # Not in the registry and not on PATH: let the backend try the
                # OS handler (os.startfile / simulated window). May still fail.
                handle = self.backend.launch_app(
                    (name,), app_name=name, window_title=name.title()
                )
        except BackendError as exc:
            raise AppLaunchError(
                f"I don't know how to open {name!r}: {exc}. Add it to "
                "jarvis/control/apps.py or install it first."
            ) from exc
        return handle, None

    # -------------------------------------------------------------- user folders

    def user_folder(self, folder: str) -> Path:
        """Resolve 'downloads'/'documents'/... to a real user folder."""
        key = folder.strip().lower().removesuffix(" folder")
        if key not in USER_FOLDERS:
            raise AppLaunchError(f"unknown user folder {folder!r}")
        home = Path.home()
        target = home / USER_FOLDERS[key] if USER_FOLDERS[key] else home
        if not target.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        return target

    def open_folder(self, path: str | Path) -> None:
        self.backend.open_path(str(path))

    def open_file(self, path: str | Path) -> None:
        self.backend.open_path(str(path))

    @staticmethod
    def known_apps() -> list[AppSpec]:
        return sorted(APP_REGISTRY.values(), key=lambda spec: spec.name)
