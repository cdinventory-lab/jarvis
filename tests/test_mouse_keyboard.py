"""Mouse + keyboard controller tests."""

from __future__ import annotations

import pytest

from jarvis.control.backend import BackendError
from jarvis.control.backends.simulated import SimulatedBackend
from jarvis.control.keyboard import KeyboardController, normalize_key
from jarvis.control.mouse import MouseController
from jarvis.perception.ocr import SimulatedOcr
from jarvis.perception.screenshot.service import ComputerVision


@pytest.fixture()
def sim() -> SimulatedBackend:
    backend = SimulatedBackend(launch_latency=0.0)
    backend.launch_app(["notepad.exe"], app_name="notepad", window_title="Notepad")
    return backend


class TestKeyNormalization:
    def test_common_aliases(self):
        assert normalize_key("ENTER") == "enter"
        assert normalize_key("Return") == "enter"
        assert normalize_key("Esc") == "escape"
        assert normalize_key("CTRL") == "ctrl"
        assert normalize_key("Control") == "ctrl"
        assert normalize_key("Windows") == "win"
        assert normalize_key("Page Up") == "pageup"
        assert normalize_key("Del") == "delete"

    def test_letters_numbers_and_function_keys(self):
        assert normalize_key("a") == "a"
        assert normalize_key("F5") == "f5"
        assert normalize_key("9") == "9"

    def test_unknown_key_rejected(self):
        with pytest.raises(ValueError):
            normalize_key("banana")


class TestKeyboardController:
    def test_type_goes_to_active_window(self, sim):
        keyboard = KeyboardController(sim)
        keyboard.type("Hello world")
        assert "Hello world" in sim.window_content("Notepad")

    def test_named_combos(self, sim):
        keyboard = KeyboardController(sim)
        keyboard.enter()
        keyboard.escape()
        keyboard.tab()
        keyboard.hotkey("CTRL", "S")
        keyboard.select_all()
        assert "ctrl+s" in sim.keys
        assert "ctrl+a" in sim.keys
        assert "enter" in sim.keys

    def test_paste_uses_clipboard_when_available(self, sim):
        keyboard = KeyboardController(sim)
        keyboard.paste("pasted text")
        assert "pasted text" in sim.window_content("Notepad")

    def test_arrow_validation(self, sim):
        keyboard = KeyboardController(sim)
        with pytest.raises(ValueError):
            keyboard.arrow("sideways")


class TestMouseController:
    def test_move_click_scroll_drag(self, sim):
        mouse = MouseController(sim)
        window = sim.list_windows()[0]
        mouse.move(*window.center)
        assert mouse.position() == window.center
        mouse.click()
        mouse.double_click()
        mouse.right_click()
        assert [c["type"] for c in sim.clicks][:1] == ["click"]
        mouse.scroll(-5)
        assert sim.clicks[-1] == {"type": "scroll", "amount": -5, "pos": mouse.position()}
        mouse.drag((10, 10), (50, 50))
        assert sim.clicks[-1]["type"] == "drag-end"

    def test_invalid_button(self, sim):
        mouse = MouseController(sim)
        with pytest.raises(ValueError):
            mouse.click(button="middle-left")

    def test_click_element_finds_and_clicks(self, sim):
        vision = ComputerVision(sim, SimulatedOcr())
        mouse = MouseController(sim)
        element = mouse.click_element("File", vision)
        assert element.text.startswith("File")
        last = sim.clicks[-1]
        assert last["type"] == "click"
        assert last["pos"] == element.center

    def test_click_element_missing_raises(self, sim):
        vision = ComputerVision(sim, SimulatedOcr())
        mouse = MouseController(sim)
        with pytest.raises(BackendError):
            mouse.click_element("Definitely Not On Screen", vision)
