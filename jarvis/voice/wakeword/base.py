"""Wake-word detector interface (spec section 2).

Phase 4 will provide local engines (openWakeWord, Porcupine, homebrew KWS).
The contract: a background thread listens to the microphone and fires the
callback when "Hey JARVIS" is heard - microphone audio is never streamed to
a remote service.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable


class WakeWordDetector(ABC):
    #: Phrase this detector listens for (for UI display).
    phrase: str = "Hey JARVIS"

    @abstractmethod
    def start(self, on_detected: Callable[[], None]) -> None:
        """Begin listening; call `on_detected` on each detection."""

    @abstractmethod
    def stop(self) -> None:
        """Stop listening and release the microphone."""

    @property
    @abstractmethod
    def running(self) -> bool: ...
