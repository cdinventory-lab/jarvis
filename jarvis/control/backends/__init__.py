"""Backend selection / factory."""

from __future__ import annotations

import logging

from jarvis.config.settings import Settings
from jarvis.control.backend import (
    BackendError,
    BackendUnavailableError,
    ComputerBackend,
    LaunchHandle,
    WindowInfo,
)
from jarvis.control.backends.pyautogui_backend import PyAutoGuiBackend
from jarvis.control.backends.simulated import SimScreenImage, SimulatedBackend
from jarvis.core.events import EventBus, EventKind

logger = logging.getLogger("jarvis.backends")

__all__ = [
    "BackendError",
    "BackendUnavailableError",
    "ComputerBackend",
    "LaunchHandle",
    "WindowInfo",
    "PyAutoGuiBackend",
    "SimulatedBackend",
    "SimScreenImage",
    "create_backend",
]


def create_backend(
    name: str,
    settings: Settings,
    events: EventBus | None = None,
) -> ComputerBackend:
    """Build a backend by name.

    ``auto`` tries the real backend first and falls back to the simulated one
    with a warning - so `jarvis` always starts, even on headless machines.
    """
    if name == "simulated":
        return SimulatedBackend(launch_latency=settings.simulated_launch_latency)
    if name in {"auto", "pyautogui"}:
        try:
            return PyAutoGuiBackend()
        except BackendUnavailableError as exc:
            if name == "pyautogui":
                raise
            logger.warning("real backend unavailable (%s); using simulated desktop", exc)
            if events is not None:
                events.emit(
                    EventKind.ACTIVITY,
                    f"Real computer control unavailable - using simulated desktop ({exc})",
                    level="warning",
                )
            return SimulatedBackend(launch_latency=settings.simulated_launch_latency)
    raise ValueError(f"unknown backend {name!r}")
