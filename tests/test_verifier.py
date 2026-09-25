"""Verifier tests (spec section 12)."""

from __future__ import annotations

from pathlib import Path

from jarvis.core.interrupt import InterruptFlag
from jarvis.core.planner.models import Expectation, ExpectationKind
from jarvis.perception.ocr import NullOcr, SimulatedOcr
from jarvis.perception.screenshot.service import ComputerVision
from jarvis.verification.verifier import VerificationStatus, Verifier
from tests.conftest import make_settings


def make_verifier(ocr) -> tuple[Verifier, object]:
    from jarvis.control.backends.simulated import SimulatedBackend

    backend = SimulatedBackend(launch_latency=0.0)
    settings = make_settings(Path("/tmp/jarvis-verifier-tests"))
    vision = ComputerVision(backend, ocr)
    return Verifier(backend, vision, InterruptFlag(), settings), backend


def test_window_appears_success():
    verifier, backend = make_verifier(SimulatedOcr())
    backend.launch_app(["notepad.exe"], app_name="notepad", window_title="Notepad")
    result = verifier.verify(
        Expectation(ExpectationKind.WINDOW_APPEARS, {"title_contains": "Notepad"})
    )
    assert result.status == VerificationStatus.SUCCESS
    assert "Notepad" in result.detail


def test_window_appears_failure():
    verifier, _backend = make_verifier(SimulatedOcr())
    result = verifier.verify(
        Expectation(ExpectationKind.WINDOW_APPEARS, {"title_contains": "Ghost"}),
        timeout=0.3,
    )
    assert result.status == VerificationStatus.FAILED


def test_window_closed():
    verifier, backend = make_verifier(SimulatedOcr())
    backend.launch_app(["notepad.exe"], app_name="notepad", window_title="Notepad")
    window = backend.active_window()
    result = verifier.verify(
        Expectation(ExpectationKind.WINDOW_CLOSED, {"title_contains": "Notepad"}),
        timeout=0.3,
    )
    assert result.status == VerificationStatus.FAILED
    backend.close_window(window.id)
    result = verifier.verify(
        Expectation(ExpectationKind.WINDOW_CLOSED, {"title_contains": "Notepad"})
    )
    assert result.status == VerificationStatus.SUCCESS


def test_process_running():
    verifier, backend = make_verifier(SimulatedOcr())
    result = verifier.verify(
        Expectation(ExpectationKind.PROCESS_RUNNING, {"name": "blender"}), timeout=0.3
    )
    assert result.status == VerificationStatus.FAILED
    backend.launch_app(["blender.exe"], app_name="blender", window_title="Blender")
    result = verifier.verify(
        Expectation(ExpectationKind.PROCESS_RUNNING, {"name": "blender"})
    )
    assert result.status == VerificationStatus.SUCCESS


def test_file_and_dir_exist(tmp_path):
    verifier, _backend = make_verifier(SimulatedOcr())
    missing = verifier.verify(
        Expectation(ExpectationKind.FILE_EXISTS, {"path": str(tmp_path / "x.txt")}),
        timeout=0.2,
    )
    assert missing.status == VerificationStatus.FAILED
    target = tmp_path / "x.txt"
    target.write_text("hi")
    found = verifier.verify(
        Expectation(ExpectationKind.FILE_EXISTS, {"path": str(target)})
    )
    assert found.status == VerificationStatus.SUCCESS
    folder = verifier.verify(
        Expectation(ExpectationKind.DIR_EXISTS, {"path": str(tmp_path)})
    )
    assert folder.status == VerificationStatus.SUCCESS


def test_screen_contains_text():
    verifier, backend = make_verifier(SimulatedOcr())
    backend.launch_app(["notepad.exe"], app_name="notepad", window_title="Notepad")
    backend.type_text("Hello JARVIS")
    result = verifier.verify(
        Expectation(ExpectationKind.SCREEN_CONTAINS_TEXT, {"text": "Hello JARVIS"})
    )
    assert result.status == VerificationStatus.SUCCESS
    result = verifier.verify(
        Expectation(ExpectationKind.SCREEN_CONTAINS_TEXT, {"text": "not visible"}),
        timeout=0.2,
    )
    assert result.status == VerificationStatus.FAILED


def test_screen_text_without_ocr_is_unknown_not_failed():
    verifier, backend = make_verifier(NullOcr())
    backend.launch_app(["notepad.exe"], app_name="notepad", window_title="Notepad")
    backend.type_text("Hello JARVIS")
    result = verifier.verify(
        Expectation(ExpectationKind.SCREEN_CONTAINS_TEXT, {"text": "Hello JARVIS"}),
        timeout=0.2,
    )
    assert result.status == VerificationStatus.UNKNOWN
    assert "no OCR" in result.detail


def test_screen_text_without_ocr_strict_asks_user():
    verifier, backend = make_verifier(NullOcr())
    verifier.settings = verifier.settings.with_overrides(verify_strict=True)
    backend.launch_app(["notepad.exe"], app_name="notepad", window_title="Notepad")
    result = verifier.verify(
        Expectation(ExpectationKind.SCREEN_CONTAINS_TEXT, {"text": "Hello"}),
        timeout=0.2,
    )
    assert result.status == VerificationStatus.NEEDS_USER


def test_none_expectation_is_unknown():
    verifier, _backend = make_verifier(SimulatedOcr())
    result = verifier.verify(Expectation(ExpectationKind.NONE))
    assert result.status == VerificationStatus.UNKNOWN


def test_interrupted_verification_fails_fast():
    verifier, backend = make_verifier(SimulatedOcr())
    verifier.interrupt.request_stop("test")
    result = verifier.verify(
        Expectation(ExpectationKind.WINDOW_APPEARS, {"title_contains": "Never"}),
        timeout=5,
    )
    assert result.status == VerificationStatus.FAILED
    assert result.detail == "interrupted"
