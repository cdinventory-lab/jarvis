"""Shared planning models (spec sections 4, 11, 12, 13).

These dataclasses are the contract between the brain (which produces plans),
the orchestrator (which executes them), the verifier (which checks expected
outcomes) and task memory (which records progress).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from jarvis.core.status import TaskStatus
from jarvis.security.permissions import RiskLevel


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExpectationKind(str, Enum):
    """What should be true in the world after an action (spec section 12)."""

    NONE = "none"
    WINDOW_APPEARS = "window_appears"      # a window matching hints exists
    WINDOW_CLOSED = "window_closed"        # no window matching hints remains
    ACTIVE_WINDOW = "active_window"        # a matching window is focused
    PROCESS_RUNNING = "process_running"    # a process name is running
    FILE_EXISTS = "file_exists"
    DIR_EXISTS = "dir_exists"
    SCREEN_CONTAINS_TEXT = "screen_contains_text"  # OCR sees the text


@dataclass(frozen=True)
class Expectation:
    kind: ExpectationKind
    params: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Intent:
    """One understood unit of user intent (Phase 1: rule-based; Phase 2: LLM)."""

    name: str
    slots: dict[str, Any]
    raw: str
    confidence: float = 1.0


@dataclass
class Step:
    """A single planned action with its risk level and expected outcome."""

    step_id: str
    action: str  # tool name
    params: dict[str, Any]
    description: str
    risk: RiskLevel = RiskLevel.LOW
    expectation: Expectation = Expectation(ExpectationKind.NONE)
    status: StepStatus = StepStatus.PENDING
    attempts: int = 0
    detail: str = ""


@dataclass
class Plan:
    task: str
    steps: list[Step] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    #: for meta-intents (greeting/help) the brain replies directly.
    direct_reply: str | None = None

    @property
    def pending(self) -> list[Step]:
        return [step for step in self.steps if step.status == StepStatus.PENDING]

    def describe(self) -> str:
        return " -> ".join(f"{i + 1}) {step.description}" for i, step in enumerate(self.steps))


@dataclass
class TaskResult:
    """Outcome of one whole task run."""

    request: str
    status: TaskStatus
    steps: list[Step] = field(default_factory=list)
    summary: str = ""
    error: str = ""

    @property
    def completed(self) -> bool:
        return self.status == TaskStatus.COMPLETED
