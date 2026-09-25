"""Console speaker: prints what JARVIS 'says' (Phase 1 stand-in for TTS)."""

from __future__ import annotations

from jarvis.voice.text_to_speech.base import Speaker


class ConsoleSpeaker(Speaker):
    def __init__(self, prefix: str = "JARVIS") -> None:
        self.prefix = prefix

    def speak(self, text: str) -> None:
        # The UI already renders SPEECH events; keep this quiet to avoid
        # double printing when an event bus is attached.
        _ = (self.prefix, text)
