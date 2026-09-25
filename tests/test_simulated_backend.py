"""Simulated backend (virtual desktop) tests."""

from __future__ import annotations

import pytest

from jarvis.control.backend import BackendError
from jarvis.control.backends.simulated import SimulatedBackend


@pytest.fixture()
def sim() -> SimulatedBackend:
    return SimulatedBackend(launch_latency=0.0)


def test_launch_creates_window_and_process(sim):
    handle = sim.launch_app(["notepad.exe"], app_name="notepad", window_title="Notepad")
    assert handle.simulated and handle.pid
    windows = sim.list_windows()
    assert len(windows) == 1
    assert windows[0].title == "Notepad"
    assert windows[0].active
    assert sim.process_exists("notepad")
    assert sim.process_exists("notepad.exe")
    assert "notepad.exe" in sim.list_processes()


def test_launch_latency_defers_window(sim):
    sim2 = SimulatedBackend(launch_latency=0.5)
    sim2.launch_app(["notepad.exe"], app_name="notepad", window_title="Notepad")
    assert sim2.list_windows() == []  # not yet visible
    assert sim2.active_window() is None


def test_typing_goes_to_active_window(sim):
    sim.launch_app(["notepad.exe"], app_name="notepad", window_title="Notepad")
    sim.type_text("Hello JARVIS")
    assert "Hello JARVIS" in sim.window_content("Notepad")


def test_typing_without_window_fails(sim):
    with pytest.raises(BackendError):
        sim.type_text("oops")


def test_click_focuses_window_under_cursor(sim):
    sim.launch_app(["notepad.exe"], app_name="notepad", window_title="Notepad")
    sim.launch_app(["chrome.exe"], app_name="chrome", window_title="Chrome")
    assert sim.active_window().title == "Chrome"
    # Chrome overlaps Notepad, so get Chrome out of the way first.
    sim.minimize_window(sim.active_window().id)
    notepad = sim.list_windows()[0]
    cx, cy = notepad.center
    sim.click(cx, cy)
    assert sim.active_window().title == "Notepad"
    assert sim.clicks[-1]["type"] == "click"


def test_close_activates_next_window(sim):
    sim.launch_app(["notepad.exe"], app_name="notepad", window_title="Notepad")
    sim.launch_app(["chrome.exe"], app_name="chrome", window_title="Chrome")
    chrome = sim.active_window()
    sim.close_window(chrome.id)
    titles = [w.title for w in sim.list_windows()]
    assert titles == ["Notepad"]
    assert sim.active_window().title == "Notepad"


def test_minimize_and_maximize(sim):
    sim.launch_app(["notepad.exe"], app_name="notepad", window_title="Notepad")
    window = sim.active_window()
    sim.minimize_window(window.id)
    assert sim.active_window() is None
    assert sim.list_windows()[0].minimized
    sim.maximize_window(window.id)
    maximized = sim.list_windows()[0]
    assert not maximized.minimized
    assert maximized.box == (0, 0, *sim.screen_size())


def test_screenshot_contains_text_blocks(sim):
    sim.launch_app(["notepad.exe"], app_name="notepad", window_title="Notepad")
    sim.type_text("visible text")
    image = sim.screenshot()
    texts = [text for text, _box in image.blocks]
    assert any("Notepad" in t for t in texts)
    assert any("visible text" in t for t in texts)


def test_open_url_creates_browser_window(sim):
    sim.open_url("https://example.com", title_hint="Example Domain")
    window = sim.active_window()
    assert window.title == "Example Domain"
    assert "https://example.com" in sim.window_content("Example Domain")


def test_open_path_missing_raises(sim, tmp_path):
    with pytest.raises(BackendError):
        sim.open_path(str(tmp_path / "nope"))


def test_keys_and_hotkeys_recorded(sim):
    sim.launch_app(["notepad.exe"], app_name="notepad", window_title="Notepad")
    sim.press_key("enter")
    sim.hotkey("ctrl", "s")
    assert sim.keys == ["enter", "ctrl+s"]
    assert sim.window_content("Notepad")[-1] == ""  # enter added a line


def test_clipboard_roundtrip(sim):
    sim.clipboard_set("hello")
    assert sim.clipboard_get() == "hello"
