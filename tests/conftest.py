"""Shared fixtures: a fully wired assistant on the simulated backend."""

from __future__ import annotations

import pytest

from jarvis.app import build_assistant
from jarvis.config.settings import Settings
from jarvis.core.events import EventBus


def make_settings(tmp_path, **overrides) -> Settings:
    env = {
        "JARVIS_BACKEND": "simulated",
        "JARVIS_DATA_DIR": str(tmp_path / "data"),
        "JARVIS_SIMULATED_LAUNCH_LATENCY": "0.0",
        "JARVIS_VERIFY_TIMEOUT": "2",
    }
    env.update(overrides)
    return Settings.load(env=env)


@pytest.fixture()
def settings(tmp_path) -> Settings:
    return make_settings(tmp_path)


@pytest.fixture()
def events() -> EventBus:
    return EventBus()


@pytest.fixture()
def assistant(tmp_path, events):
    return build_assistant(make_settings(tmp_path), events=events)


@pytest.fixture()
def medium_assistant(tmp_path, events):
    """Assistant that auto-approves medium-risk actions (scripted runs)."""
    return build_assistant(make_settings(tmp_path, JARVIS_AUTO_APPROVE_RISK="medium"), events=events)
