"""Built-in tools (spec section 18).

Each tool is a thin, testable adapter over a controller. Tools raise/return
:class:`ToolError` on failure - the orchestrator decides how to recover.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from jarvis.control.apps import AppLauncher, resolve_app_name
from jarvis.control.backend import BackendError, ComputerBackend
from jarvis.control.filesystem import (
    FilesystemController,
    FilesystemError,
    is_protected_path,
)
from jarvis.control.keyboard import KeyboardController
from jarvis.control.mouse import MouseController
from jarvis.control.terminal import (
    TerminalError,
    TerminalResult,
    TerminalRunner,
    TerminalSecurityError,
)
from jarvis.control.windows import WindowController, WindowError
from jarvis.perception.screenshot.service import ComputerVision
from jarvis.security.permissions import RiskLevel
from jarvis.tools.base import Tool, ToolRegistry, ToolResult


@dataclass
class ControllerKit:
    """Everything the built-in tools operate with."""

    backend: ComputerBackend
    mouse: MouseController
    keyboard: KeyboardController
    windows: WindowController
    launcher: AppLauncher
    filesystem: FilesystemController
    terminal: TerminalRunner
    vision: ComputerVision
    screenshots_dir: Path


def _err(detail: str) -> ToolResult:
    return ToolResult(ok=False, detail=detail)


# --------------------------------------------------------------------------- #
# Tool factories
# --------------------------------------------------------------------------- #


def _tool_open_app(kit: ControllerKit) -> Tool:
    def execute(params: dict[str, Any]) -> ToolResult:
        app = str(params.get("app", "")).strip()
        if not app:
            return _err("no app name given")
        try:
            if params.get("generic"):
                handle, spec = kit.launcher.launch_by_name(app)
                name = spec.display if spec else app
                return ToolResult(
                    True,
                    f"launched {name} (pid {handle.pid})",
                    {"app": name, "generic": spec is None},
                )
            spec = resolve_app_name(app)
            if spec is None:
                return _err(f"unknown app {app!r}")
            handle = kit.launcher.launch(spec)
            return ToolResult(
                True,
                f"launched {spec.display} (pid {handle.pid})",
                {"app": spec.display, "titles": list(spec.window_titles)},
            )
        except Exception as exc:  # AppLaunchError, BackendError
            return _err(f"could not launch {app!r}: {exc}")

    return Tool(
        name="open_app",
        description="Launch an application by name (e.g. 'notepad', 'chrome', 'blender').",
        parameters={"app": "application name", "generic": "bool - resolve via PATH"},
        category="windows",
        risk=RiskLevel.LOW,
        risk_for=lambda p: RiskLevel.MEDIUM if p.get("generic") else RiskLevel.LOW,
        execute=execute,
    )


def _tool_close_app(kit: ControllerKit) -> Tool:
    def execute(params: dict[str, Any]) -> ToolResult:
        try:
            if params.get("active"):
                active = kit.windows.active()
                if active is None:
                    return _err("no active window to close")
                kit.windows.close(active)
                return ToolResult(True, f"closed {active.title!r}", {"title": active.title})
            title = str(params.get("title_contains", ""))
            count = kit.windows.close_app(title_contains=title)
            if count == 0:
                return _err(f"no open window matches {title!r}")
            return ToolResult(True, f"closed {count} window(s) matching {title!r}")
        except WindowError as exc:
            return _err(str(exc))

    return Tool(
        name="close_app",
        description="Close windows of an app, or the active window.",
        parameters={"title_contains": "title substring", "active": "bool"},
        category="windows",
        execute=execute,
    )


def _tool_focus_window(kit: ControllerKit) -> Tool:
    def execute(params: dict[str, Any]) -> ToolResult:
        try:
            if params.get("active"):
                active = kit.windows.active()
                if active is None:
                    return _err("no window is active")
                kit.windows.activate(active)
                return ToolResult(True, f"focused {active.title!r}")
            title = str(params.get("title_contains", ""))
            window = kit.windows.focus_app(title_contains=title)
            return ToolResult(True, f"focused {window.title!r}", {"title": window.title})
        except WindowError as exc:
            return _err(str(exc))

    return Tool(
        name="focus_window",
        description="Bring a window to the foreground by (partial) title.",
        parameters={"title_contains": "title substring"},
        category="windows",
        execute=execute,
    )


def _window_target_tool(kit: ControllerKit, action: str) -> Tool:
    verb = {"minimize": "minimized", "maximize": "maximized"}[action]

    def execute(params: dict[str, Any]) -> ToolResult:
        title = params.get("title_contains")
        window = kit.windows.active() if (params.get("active") or not title) else None
        if window is None and title:
            window = kit.windows.find(title_contains=str(title))
        if window is None:
            return _err("no matching window is open")
        try:
            if action == "minimize":
                kit.windows.minimize(window)
            else:
                kit.windows.maximize(window)
        except (WindowError, BackendError) as exc:
            return _err(str(exc))
        return ToolResult(True, f"{verb} {window.title!r}")

    return Tool(
        name=f"{action}_window",
        description=f"{action.capitalize()} a window.",
        parameters={"title_contains": "title substring", "active": "bool"},
        category="windows",
        execute=execute,
    )


def _tool_list_windows(kit: ControllerKit) -> Tool:
    def execute(params: dict[str, Any]) -> ToolResult:
        windows = kit.windows.windows()
        if not windows:
            return ToolResult(True, "no open windows")
        listing = "; ".join(
            f"{w.title!r}{' (active)' if w.active else ''}" for w in windows[:12]
        )
        return ToolResult(True, f"{len(windows)} window(s): {listing}",
                          {"windows": [w.title for w in windows]})

    return Tool(
        name="list_windows",
        description="List currently open windows.",
        parameters={},
        category="windows",
        execute=execute,
    )


def _tool_type_text(kit: ControllerKit) -> Tool:
    def execute(params: dict[str, Any]) -> ToolResult:
        text = str(params.get("text", ""))
        if not text:
            return _err("nothing to type")
        try:
            kit.keyboard.type(text)
        except BackendError as exc:
            return _err(str(exc))
        return ToolResult(True, f"typed {text!r}", {"text": text})

    return Tool(
        name="type_text",
        description="Type text into the focused window.",
        parameters={"text": "string to type"},
        category="keyboard",
        execute=execute,
    )


def _tool_press_key(kit: ControllerKit) -> Tool:
    def execute(params: dict[str, Any]) -> ToolResult:
        key = str(params.get("key", ""))
        try:
            kit.keyboard.press(key)
        except ValueError as exc:
            return _err(str(exc))
        return ToolResult(True, f"pressed {key}")

    return Tool(
        name="press_key",
        description="Press a single key ('enter', 'escape', 'f5'...).",
        parameters={"key": "key name"},
        category="keyboard",
        execute=execute,
    )


def _tool_hotkey(kit: ControllerKit) -> Tool:
    def execute(params: dict[str, Any]) -> ToolResult:
        keys = [str(k) for k in params.get("keys", [])]
        if not keys:
            return _err("no keys given")
        try:
            kit.keyboard.hotkey(*keys)
        except ValueError as exc:
            return _err(str(exc))
        return ToolResult(True, f"pressed {'+'.join(keys)}")

    return Tool(
        name="hotkey",
        description="Press a key combination, e.g. ['ctrl', 's'].",
        parameters={"keys": "list of key names"},
        category="keyboard",
        execute=execute,
    )


def _tool_click_element(kit: ControllerKit) -> Tool:
    def execute(params: dict[str, Any]) -> ToolResult:
        description = str(params.get("element", ""))
        try:
            element = kit.mouse.click_element(description, kit.vision)
        except BackendError as exc:
            return _err(str(exc))
        return ToolResult(True, f"clicked {element.text!r} at {element.center}",
                          {"box": element.box})

    return Tool(
        name="click_element",
        description="Visually find an element by its visible text and click it.",
        parameters={"element": "visible text of the element"},
        category="mouse",
        execute=execute,
    )


def _tool_click_position(kit: ControllerKit) -> Tool:
    def execute(params: dict[str, Any]) -> ToolResult:
        try:
            x, y = int(params["x"]), int(params["y"])
        except (KeyError, TypeError, ValueError):
            return _err("click_position needs integer 'x' and 'y'")
        width, height = kit.backend.screen_size()
        if not (0 <= x < width and 0 <= y < height):
            return _err(f"({x}, {y}) is outside the screen ({width}x{height})")
        kit.mouse.click(x=x, y=y)
        return ToolResult(True, f"clicked ({x}, {y})")

    return Tool(
        name="click_position",
        description="Click absolute screen coordinates.",
        parameters={"x": "int", "y": "int"},
        category="mouse",
        execute=execute,
    )


def _tool_scroll(kit: ControllerKit) -> Tool:
    def execute(params: dict[str, Any]) -> ToolResult:
        amount = int(params.get("amount", 3))
        kit.mouse.scroll(amount)
        direction = "up" if amount >= 0 else "down"
        return ToolResult(True, f"scrolled {direction} by {abs(amount)}")

    return Tool(
        name="scroll",
        description="Scroll the focused window (positive=up, negative=down).",
        parameters={"amount": "int"},
        category="mouse",
        execute=execute,
    )


def _tool_screenshot(kit: ControllerKit) -> Tool:
    def execute(params: dict[str, Any]) -> ToolResult:
        image = kit.vision.screenshot()
        kit.screenshots_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        save = getattr(image, "save", None)
        if callable(save):  # PIL image
            path = kit.screenshots_dir / f"screenshot-{stamp}.png"
            save(path)
        else:  # simulated: store what the screen 'showed'
            path = kit.screenshots_dir / f"screenshot-{stamp}.txt"
            blocks = getattr(image, "blocks", ())
            path.write_text(
                "\n".join(text for text, _box in blocks), encoding="utf-8"
            )
        return ToolResult(True, f"saved screenshot to {path}", {"path": str(path)})

    return Tool(
        name="screenshot",
        description="Capture the screen and save it to the JARVIS data dir.",
        parameters={},
        category="screen",
        execute=execute,
    )


def _tool_read_screen(kit: ControllerKit) -> Tool:
    def execute(params: dict[str, Any]) -> ToolResult:
        analysis = kit.vision.analyze_screen()
        if not analysis.text_blocks:
            return ToolResult(
                False, "cannot read the screen (no OCR available)", {"text": ""}
            )
        return ToolResult(True, analysis.text, {"text": analysis.text})

    return Tool(
        name="read_screen",
        description="Read the visible text on screen (OCR).",
        parameters={},
        category="screen",
        execute=execute,
    )


def _tool_open_url(kit: ControllerKit) -> Tool:
    def execute(params: dict[str, Any]) -> ToolResult:
        url = str(params.get("url", "")).strip()
        if not url:
            return _err("no url given")
        browser = str(params.get("browser", "") or "")
        command = None
        title_hint = ""
        if browser:
            spec = resolve_app_name(browser)
            if spec is None:
                return _err(f"unknown browser {browser!r}")
            command = kit.launcher.resolve_command(spec)
            if command is None:
                command = (spec.windows[0],) if spec.windows else None
        try:
            kit.backend.open_url(url, browser_command=command, title_hint=title_hint)
        except BackendError as exc:
            return _err(f"could not open {url}: {exc}")
        return ToolResult(True, f"opened {url}", {"url": url})

    return Tool(
        name="open_url",
        description="Open a URL in a browser (optionally a specific one).",
        parameters={"url": "string", "browser": "optional browser name"},
        category="browser",
        execute=execute,
    )


def _tool_search_web(kit: ControllerKit, settings: Any) -> Tool:
    def execute(params: dict[str, Any]) -> ToolResult:
        query = str(params.get("query", "")).strip()
        if not query:
            return _err("no search query given")
        url = settings.search_url(query)
        browser = str(params.get("browser", "") or "")
        if browser:
            spec = resolve_app_name(browser)
            if spec is not None:
                try:
                    handle = kit.launcher.launch(
                        spec, url=url, title_hint=f"{query} - Search"
                    )
                    return ToolResult(
                        True,
                        f"searching for {query!r} in {spec.display} (pid {handle.pid})",
                        {"url": url},
                    )
                except Exception as exc:
                    return _err(f"could not search in {spec.display}: {exc}")
        try:
            kit.backend.open_url(url, title_hint=f"{query} - Search")
        except BackendError as exc:
            return _err(f"could not search: {exc}")
        return ToolResult(True, f"searching for {query!r}", {"url": url})

    return Tool(
        name="search_web",
        description="Search the web (opens the search engine in a browser).",
        parameters={"query": "search terms", "browser": "optional browser name"},
        category="browser",
        execute=execute,
    )


def _tool_open_folder(kit: ControllerKit) -> Tool:
    def execute(params: dict[str, Any]) -> ToolResult:
        try:
            if params.get("folder"):
                path = kit.launcher.user_folder(str(params["folder"]))
            else:
                path = kit.filesystem.expand(str(params.get("path", "")))
            opened = kit.filesystem.open_folder(path)
        except (FilesystemError, Exception) as exc:
            return _err(f"could not open folder: {exc}")
        return ToolResult(True, f"opened folder {opened}", {"path": str(opened)})

    return Tool(
        name="open_folder",
        description="Open a folder in the file explorer.",
        parameters={"folder": "well-known name (downloads...)", "path": "explicit path"},
        category="filesystem",
        execute=execute,
    )


def _tool_open_file(kit: ControllerKit) -> Tool:
    def execute(params: dict[str, Any]) -> ToolResult:
        try:
            path = kit.filesystem.open_file(str(params.get("path", "")))
        except FilesystemError as exc:
            return _err(str(exc))
        return ToolResult(True, f"opened file {path}", {"path": str(path)})

    return Tool(
        name="open_file",
        description="Open a file with its default application.",
        parameters={"path": "file path"},
        category="filesystem",
        execute=execute,
    )


def _tool_list_directory(kit: ControllerKit) -> Tool:
    def execute(params: dict[str, Any]) -> ToolResult:
        try:
            entries = kit.filesystem.list_dir(str(params.get("path", ".")))
        except FilesystemError as exc:
            return _err(str(exc))
        preview = ", ".join(
            f"{'[dir] ' if e.is_dir else ''}{e.name}" for e in entries[:15]
        )
        return ToolResult(True, f"{len(entries)} entries: {preview}",
                          {"entries": [e.name for e in entries]})

    return Tool(
        name="list_directory",
        description="List the contents of a directory.",
        parameters={"path": "directory path"},
        category="filesystem",
        execute=execute,
    )


def _tool_file_info(kit: ControllerKit) -> Tool:
    def execute(params: dict[str, Any]) -> ToolResult:
        try:
            info = kit.filesystem.metadata(str(params.get("path", "")))
        except FilesystemError as exc:
            return _err(str(exc))
        return ToolResult(True, str(info), data=info)

    return Tool(
        name="file_info",
        description="Read metadata (size, dates) for a file or folder.",
        parameters={"path": "file path"},
        category="filesystem",
        execute=execute,
    )


def _tool_create_folder(kit: ControllerKit) -> Tool:
    def execute(params: dict[str, Any]) -> ToolResult:
        try:
            path = kit.filesystem.create_folder(str(params.get("path", "")))
        except FilesystemError as exc:
            return _err(str(exc))
        return ToolResult(True, f"created folder {path}", {"path": str(path)})

    def risk_for(params: dict[str, Any]) -> RiskLevel:
        target = kit.filesystem.expand(str(params.get("path", "")))
        return RiskLevel.HIGH if is_protected_path(target) else RiskLevel.MEDIUM

    return Tool(
        name="create_folder",
        description="Create a folder (including parents).",
        parameters={"path": "folder path"},
        category="filesystem",
        risk=RiskLevel.MEDIUM,
        risk_for=risk_for,
        execute=execute,
    )


def _two_path_tool(
    kit: ControllerKit,
    name: str,
    verb: str,
    method: str,
    description: str,
) -> Tool:
    def execute(params: dict[str, Any]) -> ToolResult:
        src, dst = params.get("src"), params.get("dst")
        if not src or not dst:
            return _err(f"{name} needs 'src' and 'dst'")
        try:
            result = getattr(kit.filesystem, method)(src, dst)
        except FilesystemError as exc:
            return _err(str(exc))
        return ToolResult(True, f"{verb} -> {result}", {"path": str(result)})

    return Tool(
        name=name,
        description=description,
        parameters={"src": "source path", "dst": "destination path"},
        category="filesystem",
        risk=RiskLevel.MEDIUM,
        execute=execute,
    )


def _tool_rename_file(kit: ControllerKit) -> Tool:
    def execute(params: dict[str, Any]) -> ToolResult:
        path, new_name = params.get("path"), params.get("new_name")
        if not path or not new_name:
            return _err("rename_file needs 'path' and 'new_name'")
        try:
            result = kit.filesystem.rename(path, str(new_name))
        except FilesystemError as exc:
            return _err(str(exc))
        return ToolResult(True, f"renamed to {result}", {"path": str(result)})

    return Tool(
        name="rename_file",
        description="Rename a file or folder.",
        parameters={"path": "path", "new_name": "new name"},
        category="filesystem",
        risk=RiskLevel.MEDIUM,
        execute=execute,
    )


def _tool_search_files(kit: ControllerKit) -> Tool:
    def execute(params: dict[str, Any]) -> ToolResult:
        pattern = str(params.get("pattern", "*"))
        try:
            found = kit.filesystem.search_files(pattern, params.get("root"))
        except FilesystemError as exc:
            return _err(str(exc))
        if not found:
            return ToolResult(True, f"nothing matching {pattern!r}", {"results": []})
        preview = "; ".join(str(p) for p in found[:10])
        return ToolResult(True, f"{len(found)} match(es): {preview}",
                          {"results": [str(p) for p in found[:50]]})

    return Tool(
        name="search_files",
        description="Find files whose name matches a glob pattern.",
        parameters={"pattern": "glob pattern", "root": "search root (default home)"},
        category="filesystem",
        execute=execute,
    )


def _tool_run_command(kit: ControllerKit) -> Tool:
    def execute(params: dict[str, Any]) -> ToolResult:
        command = params.get("command")
        if not command:
            return _err("no command given")
        try:
            result: TerminalResult = kit.terminal.run(command)
        except TerminalSecurityError as exc:
            return _err(str(exc))
        except TerminalError as exc:
            return _err(str(exc))
        detail = (
            f"exit {result.returncode}: "
            f"{(result.stdout or result.stderr).strip()[:300]}"
        )
        return ToolResult(result.ok, detail,
                          {"returncode": result.returncode, "stdout": result.stdout,
                           "stderr": result.stderr})

    return Tool(
        name="run_command",
        description=(
            "Run an allowlisted terminal command (high risk - always asks "
            "unless auto-approve is raised)."
        ),
        parameters={"command": "list of argv strings"},
        category="terminal",
        risk=RiskLevel.HIGH,
        execute=execute,
    )


# --------------------------------------------------------------------------- #
# Registry construction
# --------------------------------------------------------------------------- #


def build_tools(kit: ControllerKit, settings: Any) -> ToolRegistry:
    """Register every built-in tool (spec section 18 TOOLS map)."""
    registry = ToolRegistry()
    for tool in (
        # windows
        _tool_open_app(kit),
        _tool_close_app(kit),
        _tool_focus_window(kit),
        _window_target_tool(kit, "minimize"),
        _window_target_tool(kit, "maximize"),
        _tool_list_windows(kit),
        # keyboard
        _tool_type_text(kit),
        _tool_press_key(kit),
        _tool_hotkey(kit),
        # mouse
        _tool_click_element(kit),
        _tool_click_position(kit),
        _tool_scroll(kit),
        # screen
        _tool_screenshot(kit),
        _tool_read_screen(kit),
        # browser
        _tool_open_url(kit),
        _tool_search_web(kit, settings),
        # filesystem
        _tool_open_folder(kit),
        _tool_open_file(kit),
        _tool_list_directory(kit),
        _tool_file_info(kit),
        _tool_create_folder(kit),
        _two_path_tool(kit, "copy_file", "copied", "copy", "Copy a file or folder."),
        _two_path_tool(kit, "move_file", "moved", "move", "Move a file or folder."),
        _tool_rename_file(kit),
        _tool_search_files(kit),
        # terminal
        _tool_run_command(kit),
    ):
        registry.register(tool)
    return registry
