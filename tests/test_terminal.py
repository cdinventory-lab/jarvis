"""Terminal runner tests (allowlist enforcement)."""

from __future__ import annotations

import pytest

from jarvis.control.terminal import (
    TerminalError,
    TerminalRunner,
    TerminalSecurityError,
)


@pytest.fixture()
def runner() -> TerminalRunner:
    return TerminalRunner(allowed_commands=("python", "python3", "ls"), timeout=15)


def test_allowlist_blocks_unknown_executable(runner):
    with pytest.raises(TerminalSecurityError):
        runner.run(["rm", "-rf", "/tmp"])
    with pytest.raises(TerminalSecurityError):
        runner.run("curl http://evil.example")


def test_allowlist_accepts_name_with_exe_suffix(runner):
    # .exe / .cmd suffixes are normalised away before the allowlist check
    assert runner.is_allowed(["python.exe", "-c", "pass"])
    assert runner.is_allowed(["PYTHON3", "-V"])
    assert not runner.is_allowed(["definitely-not-allowed"])


def test_allowed_command_runs(runner):
    result = runner.run(["python3", "-c", "print('ok from jarvis test')"])
    assert result.ok
    assert "ok from jarvis test" in result.stdout
    assert result.duration >= 0


def test_string_commands_are_parsed(runner):
    result = runner.run("python3 -c \"print('hi')\"")
    assert result.ok and "hi" in result.stdout


def test_failed_command_reports_returncode(runner):
    result = runner.run(["python3", "-c", "import sys; sys.exit(3)"])
    assert not result.ok
    assert result.returncode == 3


def test_missing_executable_raises(runner):
    # 'python' is allowlisted but does not exist in this sandbox PATH
    import shutil

    if shutil.which("python") is not None:
        pytest.skip("python exists on PATH; cannot test missing executable")
    with pytest.raises(TerminalError):
        runner.run(["python", "-c", "print(1)"])


def test_empty_command_rejected(runner):
    with pytest.raises((TerminalError, TerminalSecurityError)):
        runner.run([])
    with pytest.raises(TerminalError):
        runner.run("   ")
