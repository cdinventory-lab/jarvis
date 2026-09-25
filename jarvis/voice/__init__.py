"""Voice layer (spec sections 2, 3, 16 - Phase 4).

Interfaces are in place now so Phase 4 drops engines in without touching the
rest of JARVIS:
* wakeword    - local "Hey JARVIS" detection (no audio leaves the machine)
* STT         - SpeechRecognizer with local and cloud implementations
* TTS         - Speaker with a console implementation today
"""

from jarvis.voice.speech_to_text.base import AudioData, SpeechRecognizer
from jarvis.voice.text_to_speech.base import Speaker
from jarvis.voice.text_to_speech.console import ConsoleSpeaker
from jarvis.voice.wakeword.base import WakeWordDetector

__all__ = [
    "AudioData",
    "ConsoleSpeaker",
    "Speaker",
    "SpeechRecognizer",
    "WakeWordDetector",
]
