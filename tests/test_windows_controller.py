"""Window controller tests."""

from __future__ import annotations

from jarvis.control.backends.simulated import SimulatedBackend
from jarvis.control.windows import WindowController, WindowError
from jarvis.core.interrupt import InterruptFlag


def make_controller(latency: float = 0.0) -> tuple[SimulatedBackend, WindowController]:
    backend = SimulatedBackend(launch_latency=latency)
    return backend, WindowController(backend, InterruptFlag())


def test_find_and_activate():
    backend, windows = make_controller()
    backend.launch_app(["notepad.exe"], app_name="notepad", window_title="Notepad")
    backend.launch_app(["chrome.exe"], app_name="chrome", window_title="Chrome")

    found = windows.find(title_contains="Notepad")
    assert found is not None and found.title == "Notepad"
    windows.activate(found)
    assert windows.active().title == "Notepad"


def test_wait_for_polls_until_window_appears():
    backend, windows = make_controller(latency=0.3)
    backend.launch_app(["blender.exe"], app_name="blender", window_title="Blender")
    found = windows.wait_for(title_contains="Blender", timeout=3)
    assert found is not None and found.title == "Blender"


def test_wait_for_times_out_returns_none():
    backend, windows = make_controller()
    assert windows.wait_for(title_contains="Ghost", timeout=0.3) is None


def test_wait_for_is_interruptible():
    backend, windows = make_controller()
    flag = windows.interrupt
    flag.request_stop("test")
    assert windows.wait_for(title_contains="Anything", timeout=5) is None


def test_close_app_closes_all_matching():
    backend, windows = make_controller()
    backend.launch_app(["chrome.exe"], app_name="chrome", window_title="Chrome")
    backend.launch_app(["chrome.exe"], app_name="chrome", window_title="Chrome - Second")
    closed = windows.close_app(title_contains="Chrome")
    assert closed == 2
    assert windows.windows() == []


def test_wait_until_closed():
    backend, windows = make_controller()
    backend.launch_app(["notepad.exe"], app_name="notepad", window_title="Notepad")
    windows.close_app(title_contains="Notepad")
    assert windows.wait_until_closed(title_contains="Notepad", timeout=2)


def test_focus_app_missing_raises():
    _backend, windows = make_controller()
    try:
        windows.focus_app(title_contains="Nothing")
    except WindowError:
        pass
    else:
        raise AssertionError("expected WindowError")
