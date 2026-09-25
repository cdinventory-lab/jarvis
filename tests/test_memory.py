"""Task memory tests (spec section 13)."""

from __future__ import annotations

from jarvis.core.brain import RuleBasedBrain
from jarvis.core.memory import TaskMemory
from jarvis.core.planner.models import StepStatus
from jarvis.core.status import TaskStatus


def make_plan(task: str = "demo task"):
    brain = RuleBasedBrain()
    return brain.plan(
        brain.understand("open notepad and type hello"),
        {"task": task, "home": "/tmp"},
    )


def test_begin_creates_pending_steps():
    memory = TaskMemory()
    plan = make_plan()
    record = memory.begin(plan)
    assert record.status == TaskStatus.RUNNING
    assert len(record.steps) == 2
    assert all(step.status == StepStatus.PENDING for step in record.steps)


def test_update_and_state_view():
    memory = TaskMemory()
    plan = make_plan()
    record = memory.begin(plan)
    step = plan.steps[0]
    step.status = StepStatus.DONE
    memory.update_step(record, step)
    view = memory.state_view()
    assert view.task == "demo task"
    assert view.completed == [plan.steps[0].description]
    assert view.remaining == [plan.steps[1].description]


def test_finish_and_persistence(tmp_path):
    path = tmp_path / "task_memory.json"
    memory = TaskMemory(persist_path=path)
    plan = make_plan("persisted task")
    record = memory.begin(plan)
    step = plan.steps[0]
    step.status = StepStatus.DONE
    memory.update_step(record, step)
    memory.finish(record, TaskStatus.COMPLETED, "all good")

    reloaded = TaskMemory(persist_path=path)
    assert reloaded.current is not None
    assert reloaded.current.request == "persisted task"
    assert reloaded.current.status == TaskStatus.COMPLETED
    assert reloaded.current.summary == "all good"


def test_corrupt_memory_file_is_ignored(tmp_path):
    path = tmp_path / "task_memory.json"
    path.write_text("{not json at all")
    memory = TaskMemory(persist_path=path)
    assert memory.current is None


def test_recent_history_limit(tmp_path):
    memory = TaskMemory(persist_path=tmp_path / "m.json", max_history=3)
    for i in range(5):
        memory.begin(make_plan(f"task {i}"))
    assert len(memory.history) == 3
    assert memory.recent(2)[0].request == "task 4"
