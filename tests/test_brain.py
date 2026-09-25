"""Rule-based brain tests: intent parsing + plan construction."""

from __future__ import annotations

import pytest

from jarvis.core.brain import RuleBasedBrain
from jarvis.core.planner.models import ExpectationKind
from jarvis.security.permissions import RiskLevel


@pytest.fixture()
def brain() -> RuleBasedBrain:
    return RuleBasedBrain()


def names(intents):
    return [intent.name for intent in intents]


class TestUnderstanding:
    def test_open_app(self, brain):
        intents = brain.understand("Open Notepad")
        assert names(intents) == ["open_app"]
        assert intents[0].slots["app"] == "notepad"

    def test_wake_word_and_politeness(self, brain):
        intents = brain.understand("Hey JARVIS, please open Chrome for me")
        assert names(intents) == ["open_app"]
        assert intents[0].slots["app"] == "chrome"

    def test_type_preserves_case(self, brain):
        intents = brain.understand("type Hello JARVIS.")
        assert intents[0].slots["text"] == "Hello JARVIS"

    def test_type_quoted(self, brain):
        intents = brain.understand('type "Hello, world!"')
        assert intents[0].slots["text"] == "Hello, world!"

    def test_compound_and_then(self, brain):
        intents = brain.understand("Open Notepad and type Hello JARVIS")
        assert names(intents) == ["open_app", "type_text"]
        assert intents[1].slots["text"] == "Hello JARVIS"

    def test_compound_then(self, brain):
        intents = brain.understand("Open Chrome then search for blender mockups")
        assert names(intents) == ["open_app", "search_web"]

    def test_quotes_protect_connector(self, brain):
        intents = brain.understand("type 'rock and roll'")
        assert names(intents) == ["type_text"]
        assert intents[0].slots["text"] == "rock and roll"

    def test_search_with_browser(self, brain):
        intents = brain.understand("search for blender tutorials in chrome")
        assert intents[0].slots == {"query": "blender tutorials", "browser": "chrome"}

    def test_open_url(self, brain):
        intents = brain.understand("open blender.org")
        assert names(intents) == ["open_url"]
        assert intents[0].slots["url"] == "blender.org"
        assert names(brain.understand("open notepad")) == ["open_app"]

    def test_open_special_folder(self, brain):
        intents = brain.understand("open my Downloads folder")
        assert names(intents) == ["open_folder"]
        assert intents[0].slots["folder"] == "downloads"

    def test_create_folder_with_base(self, brain):
        intents = brain.understand("Create a folder named Demo in my Documents")
        assert intents[0].slots["name"] == "Demo"
        assert "documents" in intents[0].slots["base"].lower()

    def test_press_and_hotkey(self, brain):
        assert brain.understand("press enter")[0].name == "press_key"
        hotkey = brain.understand("press CTRL+SHIFT+ESC")
        assert hotkey[0].name == "hotkey"
        assert hotkey[0].slots["keys"] == ["ctrl", "shift", "escape"]

    def test_close_and_window_actions(self, brain):
        assert brain.understand("close notepad")[0].slots["target"] == "notepad"
        assert brain.understand("close the window")[0].slots["target"] == "window"
        assert brain.understand("minimize the window")[0].name == "minimize"
        assert brain.understand("maximize chrome")[0].name == "maximize"

    def test_scroll(self, brain):
        intent = brain.understand("scroll down by 5")[0]
        assert intent.slots == {"direction": "down", "amount": 5}

    def test_screenshot(self, brain):
        assert names(brain.understand("take a screenshot")) == ["screenshot"]

    def test_meta_intents(self, brain):
        assert names(brain.understand("stop")) == ["meta.stop"]
        assert names(brain.understand("cancel")) == ["meta.stop"]
        assert names(brain.understand("help")) == ["meta.help"]
        assert names(brain.understand("hello")) == ["meta.greeting"]

    def test_unknown_returns_empty(self, brain):
        assert brain.understand("make me a sandwich") == []


class TestPlanning:
    def test_notepad_demo_plan(self, brain):
        plan = brain.plan(
            brain.understand("Open Notepad and type Hello JARVIS"),
            {"task": "demo", "home": "/tmp"},
        )
        assert [s.action for s in plan.steps] == ["open_app", "type_text"]
        assert plan.steps[0].risk == RiskLevel.LOW
        assert plan.steps[0].expectation.kind == ExpectationKind.WINDOW_APPEARS
        assert plan.steps[1].expectation.kind == ExpectationKind.SCREEN_CONTAINS_TEXT
        assert plan.steps[1].expectation.params["text"] == "Hello JARVIS"

    def test_unknown_app_is_medium_risk(self, brain):
        plan = brain.plan(
            brain.understand("open someunknownapp"),
            {"task": "t", "home": "/tmp"},
        )
        assert plan.steps[0].risk == RiskLevel.MEDIUM
        assert plan.steps[0].params["generic"] is True

    def test_search_inherits_browser_from_context(self, brain):
        plan = brain.plan(
            brain.understand("Open Chrome and search for blender mockups"),
            {"task": "t", "home": "/tmp"},
        )
        search_step = plan.steps[1]
        assert search_step.action == "search_web"
        assert search_step.params["browser"] == "chrome"

    def test_create_folder_expectation(self, brain, tmp_path):
        plan = brain.plan(
            brain.understand("create folder NewProject"),
            {"task": "t", "home": str(tmp_path)},
        )
        step = plan.steps[0]
        assert step.action == "create_folder"
        assert step.risk == RiskLevel.MEDIUM
        assert step.expectation.kind == ExpectationKind.DIR_EXISTS
        assert str(tmp_path / "NewProject") == step.expectation.params["path"]

    def test_open_it_after_create_folder(self, brain, tmp_path):
        plan = brain.plan(
            brain.understand("Create a folder named X in my documents and open it"),
            {"task": "t", "home": str(tmp_path)},
        )
        assert [s.action for s in plan.steps] == ["create_folder", "open_folder"]
        assert plan.steps[1].params["path"] == str(tmp_path / "Documents" / "X")

    def test_step_ids_are_unique_and_ordered(self, brain):
        plan = brain.plan(
            brain.understand("open notepad then type hi then press enter"),
            {"task": "t", "home": "/tmp"},
        )
        ids = [s.step_id for s in plan.steps]
        assert ids == ["s1", "s2", "s3"]

    def test_meta_intents_produce_no_steps(self, brain):
        plan = brain.plan(brain.understand("help"), {"task": "t", "home": "/tmp"})
        assert plan.steps == []

    def test_meta_reply(self, brain):
        assert "open apps" in (brain.meta_reply("meta.help") or "")
