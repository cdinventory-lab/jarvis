"""Settings / configuration tests."""

from __future__ import annotations

import pytest

from jarvis.config.settings import Settings, SettingsError
from jarvis.security.permissions import RiskLevel


def test_defaults_are_safe():
    settings = Settings.load(env={})
    assert settings.backend == "auto"
    assert settings.auto_approve_risk == RiskLevel.LOW
    assert settings.max_retries == 2
    assert "python" in settings.allowed_terminal_commands


def test_env_overrides(tmp_path):
    settings = Settings.load(
        env={
            "JARVIS_BACKEND": "simulated",
            "JARVIS_AUTO_APPROVE_RISK": "medium",
            "JARVIS_MAX_RETRIES": "5",
            "JARVIS_DATA_DIR": str(tmp_path),
        }
    )
    assert settings.backend == "simulated"
    assert settings.auto_approve_risk == RiskLevel.MEDIUM
    assert settings.max_retries == 5
    assert settings.data_dir == tmp_path


def test_process_env_is_honoured(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_MAX_RETRIES", "7")
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    settings = Settings.load(env={})
    assert settings.max_retries == 7


def test_explicit_env_wins_over_process_env(monkeypatch):
    monkeypatch.setenv("JARVIS_MAX_RETRIES", "7")
    settings = Settings.load(env={"JARVIS_MAX_RETRIES": "3"})
    assert settings.max_retries == 3


def test_invalid_values_rejected():
    with pytest.raises(SettingsError):
        Settings.load(env={"JARVIS_BACKEND": "telnet"})
    with pytest.raises(SettingsError):
        Settings.load(env={"JARVIS_AUTO_APPROVE_RISK": "extreme"})
    with pytest.raises(SettingsError):
        Settings.load(env={"JARVIS_SEARCH_ENGINE": "altavista"})


def test_dotenv_file_is_parsed(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\nJARVIS_MAX_RETRIES=4\nJARVIS_LOG_LEVEL='DEBUG'\nBROKEN LINE\n"
    )
    settings = Settings.load(env={"JARVIS_DATA_DIR": str(tmp_path)}, env_file=env_file)
    assert settings.max_retries == 4
    assert settings.log_level == "DEBUG"


def test_search_url():
    settings = Settings.load(env={})
    assert "blender+tutorials" in settings.search_url("blender tutorials")
    ddg = settings.with_overrides(search_engine="duckduckgo")
    assert ddg.search_url("x").startswith("https://duckduckgo.com")


def test_safe_summary_masks_secrets():
    settings = Settings.load(env={"JARVIS_OPENAI_API_KEY": "sk-super-secret"})
    summary = settings.safe_summary()
    assert summary["openai_api_key"] == "***"
    assert "sk-super-secret" not in str(summary)
