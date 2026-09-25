"""Tool registry + built-in tool tests (spec section 18)."""

from __future__ import annotations

import pytest

from jarvis.security.permissions import RiskLevel
from jarvis.tools.base import UnknownToolError


def test_registry_lists_all_categories(assistant):
    tools = assistant.tools.all()
    categories = {tool.category for tool in tools}
    assert {"mouse", "keyboard", "screen", "browser", "filesystem", "windows",
            "terminal"} <= categories


def test_every_tool_is_dispatchable_via_metadata(assistant):
    for tool in assistant.tools.all():
        assert tool.name and tool.description and tool.parameters is not None


def test_unknown_tool_raises(assistant):
    with pytest.raises(UnknownToolError):
        assistant.tools.get("mind_control")


def test_open_app_tool(assistant):
    result = assistant.tools.dispatch("open_app", {"app": "notepad"})
    assert result.ok
    assert any("Notepad" in w.title for w in assistant.backend.list_windows())


def test_type_requires_active_window(assistant):
    result = assistant.tools.dispatch("type_text", {"text": "hi"})
    assert not result.ok  # no window is open yet


def test_click_position_bounds_checked(assistant):
    result = assistant.tools.dispatch("click_position", {"x": 99999, "y": 0})
    assert not result.ok and "outside" in result.detail


def test_click_element_on_simulated_menu(assistant):
    assistant.tools.dispatch("open_app", {"app": "notepad"})
    result = assistant.tools.dispatch("click_element", {"element": "File"})
    assert result.ok


def test_screenshot_saved(assistant):
    result = assistant.tools.dispatch("screenshot", {})
    assert result.ok
    from pathlib import Path

    assert Path(result.data["path"]).is_file()


def test_read_screen(assistant):
    assistant.tools.dispatch("open_app", {"app": "notepad"})
    assistant.tools.dispatch("type_text", {"text": "read me"})
    result = assistant.tools.dispatch("read_screen", {})
    assert result.ok and "read me" in result.data["text"]


def test_search_web_tool(assistant):
    result = assistant.tools.dispatch(
        "search_web", {"query": "blender mockups", "browser": "chrome"}
    )
    assert result.ok
    assert any("blender mockups" in w.title.lower() for w in assistant.backend.list_windows())


def test_terminal_tool_blocked_by_allowlist(assistant):
    result = assistant.tools.dispatch(
        "run_command", {"command": ["curl", "http://example.com"]}
    )
    assert not result.ok
    assert "approved command list" in result.detail


def test_risk_levels_of_tools(assistant):
    assert assistant.tools.get("run_command").risk == RiskLevel.HIGH
    assert assistant.tools.get("open_app").risk == RiskLevel.LOW
    assert assistant.tools.get("create_folder").risk == RiskLevel.MEDIUM
