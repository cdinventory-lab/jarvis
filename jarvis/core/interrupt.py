"""Interrupt system (spec section 14).

The user must always be able to stop JARVIS. An :class:`InterruptFlag` is
shared between the orchestrator, the polling loops (window waits,
verification) and every interrupt source:

* the emergency global hotkey (CTRL+ALT+J by default, Phase 1: `keyboard`
  library when installed),
* Ctrl+C in the console,
* the Stop button / ``stop`` command in the UI.

Polling helpers check the flag frequently so interrupts take effect within
~150 ms even while waiting.
"""

from __future__ import annotations

import threading
import time
from contextlib import contextmanager


class TaskInterrupted(Exception):
    """Raised inside cooperative code when a stop was requested."""


class InterruptFlag:
    """Thread-safe, cooperative stop signal."""

    def __init__(self) -> None:
        self._event = threading.Event()
        self._reason = ""
        self._lock = threading.Lock()

    def request_stop(self, reason: str = "requested by user") -> None:
        with self._lock:
            self._reason = reason
        self._event.set()

    def clear(self) -> None:
        self._event.clear()
        with self._lock:
            self._reason = ""

    @property
    def stopped(self) -> bool:
        return self._event.is_set()

    @property
    def reason(self) -> str:
        with self._lock:
            return self._reason

    def raise_if_stopped(self) -> None:
        if self._event.is_set():
            raise TaskInterrupted(self.reason)

    def sleep(self, seconds: float) -> bool:
        """Sleep for `seconds`, returning early (True) if interrupted."""
        return self._event.wait(timeout=max(0.0, seconds))

    @contextmanager
    def guard(self):
        """Context manager that raises TaskInterrupted on exit if stopped."""
        try:
            yield
        finally:
            self.raise_if_stopped()

    @staticmethod
    def wait_until(
        predicate,
        timeout: float,
        flag: InterruptFlag | None = None,
        poll_interval: float = 0.15,
    ) -> bool:
        """Poll `predicate` until true, timeout, or interruption.

        Returns True when the predicate became true; False on timeout or
        interruption (caller distinguishes via `flag.stopped`).
        """
        deadline = time.monotonic() + max(0.0, timeout)
        while True:
            if predicate():
                return True
            if flag is not None and flag.stopped:
                return False
            if time.monotonic() >= deadline:
                return False
            if flag is not None:
                flag.sleep(poll_interval)
            else:
                time.sleep(poll_interval)
