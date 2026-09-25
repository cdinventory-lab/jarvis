"""Task memory (spec section 13).

Short-term memory of the current task: which steps completed, what is
running now, what remains. This lets JARVIS recover from failures and
answer "what are you doing?". Long-term user preferences are a separate
Phase-5 concern and deliberately live elsewhere.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from jarvis.core.planner.models import Plan, Step, StepStatus
from jarvis.core.status import TaskStatus

logger = logging.getLogger("jarvis.memory")


@dataclass
class StepSnapshot:
    description: str
    action: str
    status: StepStatus
    attempts: int = 0
    detail: str = ""


@dataclass
class TaskRecord:
    task_id: str
    request: str
    created_at: datetime = field(default_factory=datetime.now)
    status: TaskStatus = TaskStatus.PENDING
    steps: list[StepSnapshot] = field(default_factory=list)
    summary: str = ""

    def step_state(self) -> dict[str, list[str]]:
        done = [s.description for s in self.steps if s.status == StepStatus.DONE]
        failed = [s.description for s in self.steps if s.status == StepStatus.FAILED]
        pending = [s.description for s in self.steps if s.status == StepStatus.PENDING]
        running = [s.description for s in self.steps if s.status == StepStatus.RUNNING]
        return {"completed": done, "failed": failed, "current": running, "remaining": pending}


@dataclass
class TaskStateView:
    """The spec-section-13 view of the current task."""

    task: str | None
    status: TaskStatus
    completed: list[str] = field(default_factory=list)
    current: list[str] = field(default_factory=list)
    remaining: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    summary: str = ""


class TaskMemory:
    """In-memory task state with optional JSON persistence."""

    def __init__(self, persist_path: Path | None = None, max_history: int = 50) -> None:
        self.persist_path = persist_path
        self.max_history = max_history
        self.history: list[TaskRecord] = []
        self._load()

    # ------------------------------------------------------------------ lifecycle

    def begin(self, plan: Plan) -> TaskRecord:
        record = TaskRecord(
            task_id=f"task-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            request=plan.task,
            status=TaskStatus.RUNNING,
            steps=[
                StepSnapshot(description=step.description, action=step.action,
                             status=StepStatus.PENDING)
                for step in plan.steps
            ],
        )
        self.history.append(record)
        del self.history[: max(0, len(self.history) - self.max_history)]
        return record

    def update_step(self, record: TaskRecord, step: Step) -> None:
        for snapshot in record.steps:
            if snapshot.description == step.description:
                snapshot.status = step.status
                snapshot.attempts = step.attempts
                snapshot.detail = step.detail
                break
        else:
            record.steps.append(
                StepSnapshot(step.description, step.action, step.status, step.attempts, step.detail)
            )

    def finish(self, record: TaskRecord, status: TaskStatus, summary: str = "") -> None:
        record.status = status
        record.summary = summary
        self._save()

    # -------------------------------------------------------------------- views

    @property
    def current(self) -> TaskRecord | None:
        return self.history[-1] if self.history else None

    def state_view(self) -> TaskStateView:
        """Current-task view in the format of spec section 13."""
        record = self.current
        if record is None:
            return TaskStateView(task=None, status=TaskStatus.PENDING)
        state = record.step_state()
        return TaskStateView(
            task=record.request,
            status=record.status,
            completed=state["completed"],
            current=state["current"],
            remaining=state["remaining"],
            failed=state["failed"],
            summary=record.summary,
        )

    def recent(self, limit: int = 5) -> list[TaskRecord]:
        return list(self.history[-limit:])[::-1]

    # --------------------------------------------------------------- persistence

    def _record_to_json(self, record: TaskRecord) -> dict[str, Any]:
        data = asdict(record)
        data["created_at"] = record.created_at.isoformat()
        return data

    def _save(self) -> None:
        if self.persist_path is None:
            return
        try:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": 1,
                "tasks": [self._record_to_json(r) for r in self.history[-self.max_history :]],
            }
            self.persist_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError as exc:
            logger.warning("could not persist task memory: %s", exc)

    def _load(self) -> None:
        if self.persist_path is None or not self.persist_path.is_file():
            return
        try:
            payload = json.loads(self.persist_path.read_text(encoding="utf-8"))
            for raw in payload.get("tasks", [])[-self.max_history :]:
                record = TaskRecord(
                    task_id=raw["task_id"],
                    request=raw["request"],
                    created_at=datetime.fromisoformat(raw["created_at"]),
                    status=TaskStatus(raw["status"]),
                    steps=[StepSnapshot(**step) for step in raw.get("steps", [])],
                    summary=raw.get("summary", ""),
                )
                self.history.append(record)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            logger.warning("could not load task memory (%s); starting fresh", exc)
