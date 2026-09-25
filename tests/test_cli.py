"""CLI tests: one-shot commands, doctor, listing."""

from __future__ import annotations

import pytest

from jarvis.cli import main


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_BACKEND", "simulated")
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path / "cli-data"))
    monkeypatch.setenv("JARVIS_SIMULATED_LAUNCH_LATENCY", "0.0")
    monkeypatch.setenv("JARVIS_VERIFY_TIMEOUT", "2")


def test_one_shot_demo_command(env, capsys):
    code = main(["Open Notepad and type Hello JARVIS."])
    assert code == 0
    out = capsys.readouterr().out
    assert "Launch Notepad" in out
    assert "Task completed" in out


def test_one_shot_needs_user_returns_nonzero(env, capsys):
    code = main(["fetch me a coffee"])
    assert code == 2  # NEEDS_USER


def test_doctor(env, capsys):
    assert main(["--doctor"]) == 0
    out = capsys.readouterr().out
    assert "JARVIS environment report" in out
    assert "pyautogui" in out


def test_list_apps(env, capsys):
    assert main(["--list-apps"]) == 0
    out = capsys.readouterr().out
    assert "notepad" in out and "chrome" in out and "blender" in out


def test_list_tools(env, capsys):
    assert main(["--list-tools"]) == 0
    out = capsys.readouterr().out
    for expected in ("open_app", "type_text", "search_web", "create_folder",
                     "run_command", "screenshot"):
        assert expected in out


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0


def test_backend_override_flag(env, capsys):
    code = main(["--backend", "simulated", "Open Notepad."])
    assert code == 0
