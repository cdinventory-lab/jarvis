"""Event bus tests."""

from __future__ import annotations

from jarvis.core.events import Event, EventBus, EventKind


def test_subscribe_and_emit():
    bus = EventBus()
    seen: list[Event] = []
    unsubscribe = bus.subscribe(seen.append)
    bus.emit(EventKind.STATUS, "Thinking", status="thinking")
    bus.emit("activity", "Working")  # string kinds are accepted
    assert len(seen) == 2
    assert seen[0].kind == EventKind.STATUS
    assert seen[1].message == "Working"
    unsubscribe()
    bus.emit(EventKind.STATUS, "Complete")
    assert len(seen) == 2


def test_history_is_bounded_and_ordered():
    bus = EventBus(history_size=5)
    for i in range(10):
        bus.emit(EventKind.ACTIVITY, f"event {i}")
    messages = [event.message for event in bus.history]
    assert len(messages) == 5
    assert messages[0] == "event 5" and messages[-1] == "event 9"


def test_broken_subscriber_does_not_break_the_bus():
    bus = EventBus()
    ok: list[Event] = []

    def broken(_event):
        raise RuntimeError("viewer crashed")

    bus.subscribe(broken)
    bus.subscribe(ok.append)
    event = bus.emit(EventKind.ACTIVITY, "still works")
    assert event.message == "still works"
    assert len(ok) == 1
