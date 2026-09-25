"""Speech-to-text abstraction (spec section 3).

Local and cloud recognizers implement the same interface; JARVIS keeps
working offline when a local model is configured. Audio never leaves the
machine unless a cloud recognizer is explicitly chosen.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AudioData:
    """Raw captured speech (backend-specific payload + metadata)."""

    payload: object
    sample_rate: int = 16_000
    duration: float = 0.0
    source: str = "microphone"

    def save(self, path: str | Path) -> Path:  # pragma: no cover - engine specific
        target = Path(path)
        target.write_bytes(self.payload if isinstance(self.payload, bytes) else b"")
        return target


class SpeechRecognizer(ABC):
    """Exactly the interface from spec section 3."""

    @abstractmethod
    def listen(self) -> AudioData | None:
        """Capture speech from the microphone (None when nothing was said)."""

    @abstractmethod
    def transcribe(self, audio: AudioData) -> str:
        """Convert captured audio to text."""
