"""Event bus: the backbone that keeps the UI, logging and agent decoupled.

Any component can emit an event (activity, tool call, verification result,
status change...). The console UI today - and a desktop/web UI later -
subscribes without the agent knowing anything about its viewers.
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger("jarvis.events")


class EventKind(str, Enum):
    STATUS = "status"
    ACTIVITY = "activity"
    USER_INPUT = "user_input"
    PLAN = "plan"
    TOOL_CALL = "tool_call"
    VERIFICATION = "verification"
    APPROVAL = "approval"
    ERROR = "error"
    SPEECH = "speech"
    TASK = "task"


@dataclass(frozen=True)
class Event:
    """A single observable moment in JARVIS's operation."""

    ts: datetime
    kind: EventKind
    message: str
    level: str = "info"
    data: dict = field(default_factory=dict)


Subscriber = Callable[[Event], None]


class EventBus:
    """Minimal synchronous pub/sub with bounded history."""

    def __init__(self, history_size: int = 1000) -> None:
        self._subscribers: list[Subscriber] = []
        self._history: deque[Event] = deque(maxlen=history_size)
        self._lock = threading.Lock()

    def subscribe(self, callback: Subscriber) -> Callable[[], None]:
        """Register a callback; returns an unsubscribe function."""
        with self._lock:
            self._subscribers.append(callback)

        def _unsubscribe() -> None:
            with self._lock:
                if callback in self._subscribers:
                    self._subscribers.remove(callback)

        return _unsubscribe

    def emit(
        self,
        kind: EventKind | str,
        message: str,
        level: str = "info",
        **data: object,
    ) -> Event:
        """Publish an event to all subscribers (exceptions are contained)."""
        if isinstance(kind, str):
            kind = EventKind(kind)
        event = Event(
            ts=datetime.now(),
            kind=kind,
            message=message,
            level=level,
            data=dict(data),
        )
        with self._lock:
            self._history.append(event)
            subscribers = tuple(self._subscribers)
        logger.debug("event %s: %s", kind.value, message)
        for callback in subscribers:
            try:
                callback(event)
            except Exception:  # noqa: BLE001 - a broken viewer must never stop the agent
                logger.exception("event subscriber failed")
        return event

    @property
    def history(self) -> tuple[Event, ...]:
        with self._lock:
            return tuple(self._history)
