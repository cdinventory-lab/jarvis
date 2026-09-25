"""Text-to-speech interface (spec section 16)."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Speaker(ABC):
    """Voice output. Implementations: ConsoleSpeaker (now), SAPI/pyttsx3 (Phase 4)."""

    #: voice / rate / volume / verbosity are configurable via Settings.
    @abstractmethod
    def speak(self, text: str) -> None:
        """Speak (or otherwise render) the given text."""
