"""Logging setup: rotating file log plus optional console output.

The file log is for debugging and never contains secrets (see Settings).
The user-facing activity feed is the EventBus - logging is separate on purpose.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys

from jarvis.config.settings import Settings

_FORMAT_FILE = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
_FORMAT_CONSOLE = "%(levelname)s %(name)s: %(message)s"


def setup_logging(settings: Settings, console: bool = False) -> logging.Logger:
    """Configure the 'jarvis' logger tree. Safe to call more than once."""
    root = logging.getLogger("jarvis")
    root.setLevel(logging.DEBUG)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    try:
        settings.logs_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            settings.logs_dir / "jarvis.log",
            maxBytes=2_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
        file_handler.setFormatter(logging.Formatter(_FORMAT_FILE))
        root.addHandler(file_handler)
    except OSError:
        # No writable data dir should never stop the assistant.
        root.addHandler(logging.NullHandler())

    if console:
        stream_handler = logging.StreamHandler(stream=sys.stderr)
        stream_handler.setLevel(logging.DEBUG if settings.verbose else logging.WARNING)
        stream_handler.setFormatter(logging.Formatter(_FORMAT_CONSOLE))
        root.addHandler(stream_handler)

    root.propagate = False
    return root
