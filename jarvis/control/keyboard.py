"""Keyboard controller (spec section 7).

Accepts human key names in any case ("ENTER", "ctrl", "Page Up") and
normalises them for the backend. Provides typed helpers for the classic
combos (copy / paste / select all / save ...).
"""

from __future__ import annotations

import re

from jarvis.control.backend import BackendError, ComputerBackend

#: Normalisation map for common aliases -> canonical key names.
_KEY_ALIASES: dict[str, str] = {
    "return": "enter",
    "esc": "escape",
    "control": "ctrl",
    "ctl": "ctrl",
    "cmd": "win",
    "super": "win",
    "meta": "win",
    "windows": "win",
    "option": "alt",
    "del": "delete",
    "pgup": "pageup",
    "pgdn": "pagedown",
    "pgdown": "pagedown",
    "spacebar": "space",
    "printscreen": "printscreen",
    "ins": "insert",
}

_VALID_KEY = re.compile(r"^(f\d{1,2}|[a-z0-9])$")

#: Canonical multi-character key names accepted by the backends.
_KNOWN_KEYS = {
    "enter", "escape", "ctrl", "alt", "shift", "win", "space", "tab",
    "up", "down", "left", "right", "pageup", "pagedown", "home", "end",
    "delete", "insert", "backspace", "capslock", "printscreen", "numlock",
    "scrolllock", "pause",
}


def normalize_key(key: str) -> str:
    """'CTRL' -> 'ctrl', 'Page Up' -> 'pageup', 'Esc' -> 'escape' ..."""
    cleaned = key.strip().lower().replace(" ", "").replace("_", "").replace("-", "")
    cleaned = _KEY_ALIASES.get(cleaned, cleaned)
    if cleaned in _KNOWN_KEYS or _VALID_KEY.match(cleaned):
        return cleaned
    raise ValueError(f"unknown key name: {key!r}")


class KeyboardController:
    """High-level keyboard control over any backend."""

    def __init__(self, backend: ComputerBackend, typing_interval: float = 0.0) -> None:
        self.backend = backend
        self.typing_interval = typing_interval

    # -------------------------------------------------------------- primitives

    def type(self, text: str, interval: float | None = None) -> None:
        """Type literal text into whatever currently has focus."""
        if not text:
            return
        self.backend.type_text(text, interval=self.typing_interval if interval is None else interval)

    def press(self, key: str) -> None:
        self.backend.press_key(normalize_key(key))

    def press_many(self, keys: list[str]) -> None:
        for key in keys:
            self.press(key)

    def hotkey(self, *keys: str) -> None:
        """Press a combination, e.g. hotkey("CTRL", "SHIFT", "ESC")."""
        if not keys:
            raise ValueError("hotkey needs at least one key")
        self.backend.hotkey(*(normalize_key(key) for key in keys))

    def key_down(self, key: str) -> None:
        self.backend.key_down(normalize_key(key))

    def key_up(self, key: str) -> None:
        self.backend.key_up(normalize_key(key))

    # ------------------------------------------------------------- named combos

    def enter(self) -> None:
        self.press("enter")

    def escape(self) -> None:
        self.press("escape")

    def tab(self) -> None:
        self.press("tab")

    def arrow(self, direction: str) -> None:
        direction = direction.strip().lower()
        if direction not in {"up", "down", "left", "right"}:
            raise ValueError(f"invalid arrow direction {direction!r}")
        self.press(direction)

    def function_key(self, number: int) -> None:
        if not 1 <= number <= 12:
            raise ValueError("function keys are F1..F12")
        self.press(f"f{number}")

    def select_all(self) -> None:
        self.hotkey("ctrl", "a")

    def copy(self) -> None:
        self.hotkey("ctrl", "c")

    def paste(self, text: str | None = None) -> None:
        """Paste the clipboard (optionally setting it to `text` first)."""
        if text is not None:
            try:
                self.backend.clipboard_set(text)
            except BackendError:
                # No clipboard support: degrade to plain typing.
                self.type(text)
                return
        self.hotkey("ctrl", "v")

    def cut(self) -> None:
        self.hotkey("ctrl", "x")

    def save(self) -> None:
        self.hotkey("ctrl", "s")
