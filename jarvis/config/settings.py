"""Configuration for JARVIS.

All settings come from environment variables (optionally a `.env` file) with
safe defaults. Secrets are only ever read from the environment - never stored
in code and never written to logs.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from jarvis.security.permissions import RiskLevel

ENV_PREFIX = "JARVIS_"

#: Search engines supported by the `search_web` tool.
SEARCH_ENGINES: dict[str, str] = {
    "google": "https://www.google.com/search?q={q}",
    "duckduckgo": "https://duckduckgo.com/?q={q}",
    "bing": "https://www.bing.com/search?q={q}",
}

#: Conservative default terminal allowlist (see SecurityPolicy / TerminalRunner).
DEFAULT_TERMINAL_ALLOWLIST: tuple[str, ...] = (
    "python",
    "python3",
    "pip",
    "pip3",
    "git",
    "node",
    "npm",
    "tasklist",
    "where",
    "ls",
    "which",
)


class SettingsError(ValueError):
    """Raised when a configuration value cannot be parsed."""


def _parse_env_file(path: Path) -> dict[str, str]:
    """Parse a minimal .env file (KEY=VALUE lines, '#' comments)."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def _to_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _to_risk(value: str) -> RiskLevel:
    try:
        return RiskLevel.parse(value)
    except ValueError as exc:
        raise SettingsError(f"invalid risk level {value!r}") from exc


def _to_tuple(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


_FIELD_PARSERS: dict[str, Any] = {
    "backend": str,
    "auto_approve_risk": _to_risk,
    "max_retries": int,
    "verify_timeout": float,
    "action_timeout": float,
    "typing_interval": float,
    "log_level": str,
    "verbose": _to_bool,
    "quiet": _to_bool,
    "data_dir": lambda v: Path(v).expanduser(),
    "emergency_stop_hotkey": str,
    "emergency_hotkey_enabled": _to_bool,
    "search_engine": str,
    "simulated_launch_latency": float,
    "verify_strict": _to_bool,
    "voice_enabled": _to_bool,
    "voice_rate": float,
    "voice_volume": float,
    "speech_verbosity": str,
    "allowed_terminal_commands": _to_tuple,
    "ai_provider": str,
    "openai_api_key": str,
}

# Keys whose values must never appear in logs or doctor output.
SECRET_KEYS = {"openai_api_key"}


@dataclass(frozen=True)
class Settings:
    """Runtime configuration. Immutable; use :meth:`with_overrides` to adjust."""

    backend: str = "auto"
    auto_approve_risk: RiskLevel = RiskLevel.LOW
    max_retries: int = 2
    verify_timeout: float = 8.0
    action_timeout: float = 15.0
    typing_interval: float = 0.03
    log_level: str = "INFO"
    verbose: bool = False
    quiet: bool = False
    data_dir: Path = field(default_factory=lambda: Path.home() / ".jarvis")
    emergency_stop_hotkey: str = "ctrl+alt+j"
    emergency_hotkey_enabled: bool = True
    search_engine: str = "google"
    simulated_launch_latency: float = 0.2
    verify_strict: bool = False
    # Voice (Phase 4) - configuration surface exists already.
    voice_enabled: bool = False
    voice_rate: float = 1.0
    voice_volume: float = 1.0
    speech_verbosity: str = "normal"
    allowed_terminal_commands: tuple[str, ...] = DEFAULT_TERMINAL_ALLOWLIST
    # AI provider (Phase 2) - rule-based brain is used until this is set.
    ai_provider: str = "none"
    openai_api_key: str = ""

    # ------------------------------------------------------------------ load

    @classmethod
    def load(
        cls,
        env: Mapping[str, str] | None = None,
        env_file: Path | None = None,
    ) -> Settings:
        """Build settings from: defaults <- .env file <- process env <- `env`.

        The explicit `env` mapping wins over everything and is what CLI flags
        and tests use to override behaviour.
        """
        merged: dict[str, str] = {}
        if env_file is None:
            # Look for .env next to the current working directory only.
            candidate = Path.cwd() / ".env"
            merged.update(_parse_env_file(candidate))
        elif env_file.is_file():
            merged.update(_parse_env_file(env_file))
        merged.update(
            {key: value for key, value in os.environ.items() if key.startswith(ENV_PREFIX)}
        )
        if env:
            merged.update(
                {key if key.startswith(ENV_PREFIX) else ENV_PREFIX + key.upper(): value
                 for key, value in env.items()}
            )

        kwargs: dict[str, Any] = {}
        for f in fields(cls):
            parser = _FIELD_PARSERS.get(f.name)
            if parser is None:
                continue
            raw = merged.get(ENV_PREFIX + f.name.upper())
            if raw is None:
                continue
            try:
                kwargs[f.name] = parser(raw)
            except (ValueError, TypeError) as exc:
                raise SettingsError(f"bad value for {ENV_PREFIX}{f.name.upper()}: {exc}") from exc

        settings = cls(**kwargs)
        if settings.backend not in {"auto", "simulated", "pyautogui"}:
            raise SettingsError(f"unknown backend {settings.backend!r}")
        if settings.search_engine not in SEARCH_ENGINES:
            raise SettingsError(
                f"unknown search engine {settings.search_engine!r}; "
                f"choose one of {sorted(SEARCH_ENGINES)}"
            )
        return settings

    def with_overrides(self, **changes: Any) -> Settings:
        """Return a copy with the given fields replaced."""
        return replace(self, **changes)

    # ------------------------------------------------------------- properties

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def memory_file(self) -> Path:
        return self.data_dir / "task_memory.json"

    @property
    def screenshots_dir(self) -> Path:
        return self.data_dir / "screenshots"

    def ensure_dirs(self) -> None:
        for path in (self.data_dir, self.logs_dir, self.screenshots_dir):
            path.mkdir(parents=True, exist_ok=True)

    def search_url(self, query: str) -> str:
        """URL for a web search with the configured engine."""
        template = SEARCH_ENGINES.get(self.search_engine, SEARCH_ENGINES["google"])
        return template.format(q=quote_plus(query))

    def safe_summary(self) -> dict[str, Any]:
        """Settings as a dict safe to print/log (secrets masked)."""
        result: dict[str, Any] = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if f.name in SECRET_KEYS:
                result[f.name] = "***" if value else ""
            elif isinstance(value, RiskLevel):
                result[f.name] = value.label
            elif isinstance(value, Path):
                result[f.name] = str(value)
            else:
                result[f.name] = value
        return result
