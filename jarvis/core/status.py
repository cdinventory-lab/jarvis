"""Agent- and task-level status enums shared across the system."""

from __future__ import annotations

from enum import Enum


class AgentStatus(str, Enum):
    """What JARVIS is doing right now (drives the UI status indicator)."""

    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETE = "complete"
    ERROR = "error"
    PAUSED = "paused"
    STOPPED = "stopped"

    @property
    def label(self) -> str:
        return self.value.capitalize()


class TaskStatus(str, Enum):
    """Outcome of a whole task (spec section 12/21)."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_USER = "needs_user"
    INTERRUPTED = "interrupted"

    @property
    def label(self) -> str:
        return self.value.replace("_", " ").capitalize()
