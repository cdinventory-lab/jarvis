"""Text-to-speech subpackage."""

from jarvis.voice.text_to_speech.base import Speaker
from jarvis.voice.text_to_speech.console import ConsoleSpeaker

__all__ = ["ConsoleSpeaker", "Speaker"]
