"""Computer-control layer: mouse, keyboard, windows, apps, files, terminal."""

from jarvis.control.backend import (
    BackendError,
    BackendUnavailableError,
    ComputerBackend,
    LaunchHandle,
    WindowInfo,
)

__all__ = [
    "BackendError",
    "BackendUnavailableError",
    "ComputerBackend",
    "LaunchHandle",
    "WindowInfo",
]
