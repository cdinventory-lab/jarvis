"""Permission-aware terminal (spec section 8: "launching approved commands").

Rules:
* the executable must be on the configured allowlist (default: python, pip,
  git, node, npm, tasklist, where, ls, which),
* commands always run with ``shell=False`` - no string interpolation, no
  injection surface,
* a hard timeout applies,
* the tool layer additionally classifies terminal use as HIGH risk, so the
  user confirms every run unless they explicitly raised the auto-approve bar.
"""

from __future__ import annotations

import logging
import shlex
import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass

logger = logging.getLogger("jarvis.terminal")


class TerminalSecurityError(RuntimeError):
    """Command refused by the allowlist."""


class TerminalError(RuntimeError):
    """Command failed to run."""


def _normalize_executable(token: str) -> str:
    name = token.strip().lower()
    for suffix in (".exe", ".cmd", ".bat", ".com"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    return name


@dataclass(frozen=True)
class TerminalResult:
    command: tuple[str, ...]
    returncode: int | None
    stdout: str
    stderr: str
    duration: float
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out


class TerminalRunner:
    def __init__(self, allowed_commands: Sequence[str], timeout: float = 60.0) -> None:
        self.allowed = {_normalize_executable(token) for token in allowed_commands}
        self.timeout = timeout

    def is_allowed(self, command: Sequence[str]) -> bool:
        if not command:
            return False
        return _normalize_executable(command[0]) in self.allowed

    def run(
        self,
        command: Sequence[str] | str,
        cwd: str | None = None,
        timeout: float | None = None,
    ) -> TerminalResult:
        cmd = self._prepare(command)
        logger.info("running command: %s", " ".join(cmd))
        started = time.monotonic()
        try:
            completed = subprocess.run(  # noqa: S603 - allowlisted, shell=False
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            return TerminalResult(
                command=tuple(cmd),
                returncode=None,
                stdout=(exc.stdout or b"").decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
                stderr=f"timed out after {timeout or self.timeout}s",
                duration=time.monotonic() - started,
                timed_out=True,
            )
        except FileNotFoundError as exc:
            raise TerminalError(f"executable not found: {cmd[0]!r}") from exc
        except OSError as exc:
            raise TerminalError(f"could not run {cmd[0]!r}: {exc}") from exc
        return TerminalResult(
            command=tuple(cmd),
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration=time.monotonic() - started,
        )

    def _prepare(self, command: Sequence[str] | str) -> list[str]:
        if isinstance(command, str):
            cmd = shlex.split(command)
        else:
            cmd = [str(part) for part in command]
        if not cmd:
            raise TerminalError("empty command")
        if not self.is_allowed(cmd):
            raise TerminalSecurityError(
                f"'{cmd[0]}' is not on the approved command list "
                f"({', '.join(sorted(self.allowed))}). Add it via "
                "JARVIS_ALLOWED_TERMINAL_COMMANDS if you really want it."
            )
        return cmd
