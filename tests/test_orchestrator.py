"""Orchestrator end-to-end tests (spec sections 11, 12, 21, 22).

These run the full observe -> understand -> plan -> act -> verify loop on
the simulated desktop - the same code path that runs with the real backend
on a Windows machine.
"""

from __future__ import annotations

import json

from jarvis.core.status import TaskStatus
from jarvis.security.permissions import RiskLevel
from tests.conftest import make_settings


def events_of(assistant, kind: str) -> list:
    return [e for e in assistant.events.history if e.kind.value == kind]


class TestFirstDemonstration:
    """Spec section 26: 'Open Notepad and type Hello JARVIS.'"""

    def test_notepad_demo_completes_with_verification(self, assistant):
        result = assistant.orchestrator.execute("Open Notepad and type Hello JARVIS.")
        assert result.status == TaskStatus.COMPLETED
        assert [s.action for s in result.steps] == ["open_app", "type_text"]
        assert all(s.status.value == "done" for s in result.steps)

        # the text really was typed into the notepad window
        assert "Hello JARVIS" in assistant.backend.window_content("Notepad")

        # and both steps were verified, not assumed
        verifications = events_of(assistant, "verification")
        assert any("window detected" in v.message for v in verifications)
        assert any("Hello JARVIS" in v.message and "found on screen" in v.message for v in verifications)

    def test_demo_event_feed_shows_the_loop(self, assistant):
        assistant.orchestrator.execute("Open Notepad and type Hello JARVIS.")
        statuses = [e.data.get("status") for e in events_of(assistant, "status")]
        for expected in ("thinking", "executing", "verifying", "complete"):
            assert expected in statuses, f"missing status {expected} in {statuses}"

    def test_summary_is_spoken(self, assistant):
        result = assistant.orchestrator.execute("Open Notepad and type Hello JARVIS.")
        assert result.status == TaskStatus.COMPLETED
        speeches = [e.message for e in events_of(assistant, "speech")]
        assert any(s.startswith("Done.") for s in speeches)


class TestCompoundTasks:
    def test_search_task(self, assistant):
        result = assistant.orchestrator.execute(
            "Open Chrome and search for Blender clothing mockups."
        )
        assert result.status == TaskStatus.COMPLETED
        titles = [w.title for w in assistant.backend.list_windows()]
        assert any("Blender clothing mockups" in t for t in titles)

    def test_create_folder_and_open_it(self, medium_assistant, tmp_path):
        result = medium_assistant.orchestrator.execute(
            "Create a folder named Jarvis Demo in my Documents and open it."
        )
        assert result.status == TaskStatus.COMPLETED
        assert (tmp_path / "data" / "..").resolve().parent.name  # sanity
        titles = [w.title for w in medium_assistant.backend.list_windows()]
        assert any("Jarvis Demo" in t for t in titles)

    def test_close_after_open(self, assistant):
        assistant.orchestrator.execute("Open Notepad.")
        result = assistant.orchestrator.execute("Close notepad.")
        assert result.status == TaskStatus.COMPLETED
        assert assistant.backend.list_windows() == []


class TestFailureAndRecovery:
    def test_unparseable_command_asks_user(self, assistant):
        result = assistant.orchestrator.execute("fetch me a coffee please")
        assert result.status == TaskStatus.NEEDS_USER
        assert "help" in result.summary.lower()

    def test_failed_step_asks_user_after_retries(self, assistant):
        # 'open folder' with a nonexistent path fails deterministically
        result = assistant.orchestrator.execute(
            "open folder /definitely/not/here/at/all"
        )
        assert result.status == TaskStatus.NEEDS_USER
        assert result.steps[0].attempts >= 2  # retried before giving up

    def test_unknown_app_is_never_blindly_executed(self, assistant):
        result = assistant.orchestrator.execute("Open definitely-not-an-app-xyz")
        # generic launch is medium risk -> default policy asks -> denied ->
        # JARVIS stops and asks the user instead of forcing it through.
        assert result.status == TaskStatus.NEEDS_USER


class TestPermissions:
    def test_medium_risk_denied_without_approval(self, assistant, tmp_path):
        result = assistant.orchestrator.execute(
            f"create folder {tmp_path / 'denied'}"
        )
        assert result.status == TaskStatus.NEEDS_USER
        assert not (tmp_path / "denied").exists()

    def test_medium_risk_approved_by_policy(self, medium_assistant, tmp_path):
        result = medium_assistant.orchestrator.execute(
            f"create folder {tmp_path / 'approved'}"
        )
        assert result.status == TaskStatus.COMPLETED
        assert (tmp_path / "approved").is_dir()

    def test_approval_events_emitted(self, medium_assistant, tmp_path):
        medium_assistant.orchestrator.execute(f"create folder {tmp_path / 'x'}")
        approvals = events_of(medium_assistant, "approval")
        assert any("auto-approved" in a.message for a in approvals)

    def test_protected_path_escalates_risk(self, tmp_path, events):
        from jarvis.app import build_assistant

        assistant = build_assistant(make_settings(tmp_path), events=events)
        tool = assistant.tools.get("create_folder")
        assert tool.risk_for({"path": "/etc/jarvis"}) == RiskLevel.HIGH
        assert tool.risk_for({"path": str(tmp_path / "ok")}) == RiskLevel.MEDIUM


class TestInterrupts:
    def test_interrupt_mid_task_stops(self, assistant):
        def stop_when_typing(event):
            if event.kind.value == "tool_call" and event.data.get("tool") == "type_text":
                assistant.interrupt.request_stop("user pressed stop")

        assistant.events.subscribe(stop_when_typing)
        result = assistant.orchestrator.execute(
            "Open Notepad and type Hello JARVIS and take a screenshot."
        )
        assert result.status == TaskStatus.INTERRUPTED
        actions = [s.action for s in result.steps]
        assert "screenshot" in actions
        assert all(s.status.value != "done" for s in result.steps if s.action == "screenshot")

    def test_stop_command_is_recognised(self, assistant):
        result = assistant.orchestrator.execute("stop")
        assert result.status == TaskStatus.COMPLETED
        assert assistant.interrupt.stopped

    def test_status_command_reports_memory(self, assistant):
        assistant.orchestrator.execute("Open Notepad.")
        result = assistant.orchestrator.execute("status")
        assert result.status == TaskStatus.COMPLETED
        assert "Open Notepad" in result.summary


class TestTaskMemoryIntegration:
    def test_memory_records_the_demo(self, assistant, tmp_path):
        assistant.orchestrator.execute("Open Notepad and type Hello JARVIS.")
        view = assistant.memory.state_view()
        assert view.status == TaskStatus.COMPLETED
        assert len(view.completed) == 2
        assert view.remaining == []

    def test_memory_persists_to_disk(self, assistant):
        assistant.orchestrator.execute("Open Notepad and type Hello JARVIS.")
        memory_file = assistant.settings.memory_file
        assert memory_file.is_file()
        payload = json.loads(memory_file.read_text())
        assert payload["tasks"], "no tasks persisted"
        assert payload["tasks"][-1]["status"] == "completed"
