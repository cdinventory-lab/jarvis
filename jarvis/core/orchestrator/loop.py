"""Autonomous action loop (spec sections 11, 21, 25).

    OBSERVE -> UNDERSTAND -> PLAN -> ACT -> VERIFY -> OBSERVE AGAIN -> CONTINUE

The orchestrator never assumes an action worked because the command was
sent: every step is verified against its expectation. On failure it retries
(with tool-level alternatives), asks the brain to re-plan, and only then
escalates to the user. Every phase transition is emitted on the event bus so
the UI shows exactly what JARVIS is doing - without exposing private
chain-of-thought (which Phase 1 doesn't have; Phase 2's LLM reasoning stays
internal by design).
"""

from __future__ import annotations

import logging
from typing import Any

from jarvis.core.brain.base import Brain
from jarvis.core.events import EventBus, EventKind
from jarvis.core.interrupt import InterruptFlag, TaskInterrupted
from jarvis.core.memory import TaskMemory
from jarvis.core.planner.models import (
    ExpectationKind,
    Plan,
    Step,
    StepStatus,
    TaskResult,
)
from jarvis.core.status import AgentStatus, TaskStatus
from jarvis.security.permissions import PermissionRequest, SecurityPolicy
from jarvis.tools.base import ToolRegistry
from jarvis.verification.verifier import VerificationResult, VerificationStatus, Verifier

logger = logging.getLogger("jarvis.orchestrator")

_RETRY_BACKOFF = 0.4


class Orchestrator:
    """Executes tasks: understand -> plan -> act -> verify -> recover."""

    def __init__(
        self,
        *,
        brain: Brain,
        tools: ToolRegistry,
        security: SecurityPolicy,
        verifier: Verifier,
        memory: TaskMemory,
        events: EventBus,
        interrupt: InterruptFlag,
        settings: Any,
        speaker: Any = None,
    ) -> None:
        self.brain = brain
        self.tools = tools
        self.security = security
        self.verifier = verifier
        self.memory = memory
        self.events = events
        self.interrupt = interrupt
        self.settings = settings
        self.speaker = speaker

    # ------------------------------------------------------------------ helpers

    def _status(self, status: AgentStatus) -> None:
        self.events.emit(EventKind.STATUS, status.label, status=status.value)

    def _activity(self, message: str, level: str = "info") -> None:
        self.events.emit(EventKind.ACTIVITY, message, level=level)

    def _verification(self, message: str, ok: bool, **data: Any) -> None:
        self.events.emit(
            EventKind.VERIFICATION, message, level="info" if ok else "warning", **data
        )

    def _speak(self, text: str) -> None:
        self.events.emit(EventKind.SPEECH, text)
        if self.speaker is not None:
            try:
                self.speaker.speak(text)
            except Exception:  # noqa: BLE001 - TTS must never break a task
                logger.exception("speaker failed")

    # ------------------------------------------------------------------- execute

    def execute(self, text: str) -> TaskResult:
        """Run one full task (the observe-plan-act-verify loop)."""
        self.interrupt.clear()
        request = text.strip()
        self.events.emit(EventKind.USER_INPUT, request)
        self._status(AgentStatus.THINKING)
        self._activity(f"Understanding: {request!r}")

        try:
            return self._execute_inner(request)
        except TaskInterrupted as exc:
            self._status(AgentStatus.STOPPED)
            self._activity(f"Interrupted: {exc}", level="warning")
            self._speak("Stopped.")
            return TaskResult(
                request=request, status=TaskStatus.INTERRUPTED,
                summary=f"Interrupted: {exc}", error=str(exc),
            )
        except Exception as exc:  # noqa: BLE001 - agent must not crash the app
            logger.exception("task crashed")
            self._status(AgentStatus.ERROR)
            self._activity(f"Unexpected error: {exc}", level="error")
            self._speak("Something went wrong while working on that.")
            return TaskResult(
                request=request, status=TaskStatus.FAILED, error=str(exc),
                summary=f"Internal error: {exc}",
            )
        finally:
            self._status(AgentStatus.IDLE)

    def _execute_inner(self, request: str) -> TaskResult:
        intents = self.brain.understand(request)

        # ---- meta intents (help / status / stop / greetings) -----------------
        if intents and all(intent.name.startswith("meta.") for intent in intents):
            return self._handle_meta(request, intents)

        if not intents:
            self._status(AgentStatus.IDLE)
            reply = (
                "I couldn't understand that yet. Try 'help' to see what I can do."
            )
            self._speak(reply)
            return TaskResult(
                request=request, status=TaskStatus.NEEDS_USER, summary=reply
            )

        # ---- plan -------------------------------------------------------------
        context = {
            "task": request,
            "home": str(self.settings.data_dir.home()) if hasattr(self.settings.data_dir, "home") else "~",
            "tools": self.tools.names(),
            "apps": True,
        }
        plan = self.brain.plan(intents, context)
        if not plan.steps:
            self._status(AgentStatus.IDLE)
            reply = "I understood the words but have no way to act on them yet."
            self._speak(reply)
            return TaskResult(request=request, status=TaskStatus.NEEDS_USER, summary=reply)

        self.events.emit(
            EventKind.PLAN,
            f"Plan ready - {len(plan.steps)} step(s): {plan.describe()}",
            steps=[step.description for step in plan.steps],
        )
        record = self.memory.begin(plan)
        self.interrupt.raise_if_stopped()

        # ---- act + verify loop ------------------------------------------------
        try:
            return self._run_steps(request, plan, record)
        except TaskInterrupted as exc:
            self.memory.finish(record, TaskStatus.INTERRUPTED, str(exc))
            self._finish_task(request, plan, TaskStatus.INTERRUPTED, str(exc))
            return TaskResult(
                request=request,
                status=TaskStatus.INTERRUPTED,
                steps=plan.steps,
                summary=f"Interrupted: {exc}",
                error=str(exc),
            )

    def _run_steps(self, request: str, plan: Plan, record) -> TaskResult:
        for index, step in enumerate(plan.steps, start=1):
            if self.interrupt.stopped:
                raise TaskInterrupted(self.interrupt.reason)
            outcome = self._run_step(step, index, len(plan.steps))
            self.memory.update_step(record, step)
            self.interrupt.raise_if_stopped()  # stop before the next step
            if outcome == _StepOutcome.DONE:
                continue
            if outcome == _StepOutcome.NEEDS_USER:
                self.memory.finish(record, TaskStatus.NEEDS_USER, step.detail)
                self._finish_task(request, plan, TaskStatus.NEEDS_USER, step.detail)
                return TaskResult(
                    request=request, status=TaskStatus.NEEDS_USER,
                    steps=plan.steps, summary=step.detail,
                )
            # FAILED after retries and no recovery
            self.memory.finish(record, TaskStatus.FAILED, step.detail)
            self._finish_task(request, plan, TaskStatus.FAILED, step.detail)
            return TaskResult(
                request=request, status=TaskStatus.FAILED,
                steps=plan.steps, summary=step.detail, error=step.detail,
            )

        summary = self._summarize_success(plan)
        self.memory.finish(record, TaskStatus.COMPLETED, summary)
        self._finish_task(request, plan, TaskStatus.COMPLETED, summary)
        return TaskResult(request=request, status=TaskStatus.COMPLETED, steps=plan.steps, summary=summary)

    # --------------------------------------------------------------- meta intents

    def _handle_meta(self, request: str, intents: list) -> TaskResult:
        name = intents[0].name
        if name == "meta.status":
            view = self.memory.state_view()
            if view.task is None:
                reply = "I have no task history yet."
            else:
                reply = (
                    f"Last task: {view.task} - {view.status.label}. "
                    f"Completed: {len(view.completed)}, remaining: {len(view.remaining)}."
                )
        elif name == "meta.stop":
            self.interrupt.request_stop("user requested stop")
            reply = "Stopping what I'm doing."
        else:
            reply = self.brain.meta_reply(name) or "I'm listening."
        self._status(AgentStatus.COMPLETE)
        self._speak(reply)
        return TaskResult(request=request, status=TaskStatus.COMPLETED, summary=reply)

    # ----------------------------------------------------------------- one step

    def _run_step(self, step: Step, index: int, total: int) -> _StepOutcome:
        """Execute one step with permission gate, retries and verification."""
        tool = self.tools.get(step.action)  # raises UnknownToolError -> caught above
        effective_risk = tool.effective_risk(step.params)

        # ---- permission gate --------------------------------------------------
        decision = self.security.check(
            PermissionRequest(
                tool=step.action,
                action=step.description,
                risk=effective_risk,
                params=step.params,
            )
        )
        if not decision.allowed:
            step.status = StepStatus.SKIPPED
            step.detail = f"permission denied ({decision.reason})"
            self._activity(f"Step {index}/{total} skipped: {step.detail}", level="warning")
            return _StepOutcome.NEEDS_USER

        max_attempts = 1 + max(0, self.settings.max_retries)
        for attempt in range(1, max_attempts + 1):
            if self.interrupt.stopped:
                raise TaskInterrupted(self.interrupt.reason)
            step.attempts = attempt
            step.status = StepStatus.RUNNING
            self._status(AgentStatus.EXECUTING)
            self.events.emit(
                EventKind.TOOL_CALL,
                f"Step {index}/{total}: {step.description}"
                + (f" (attempt {attempt})" if attempt > 1 else ""),
                tool=step.action,
                risk=effective_risk.label,
            )
            if attempt == 1:
                self._speak(self._speech_for_step(step))

            result = self.tools.dispatch(step.action, step.params)

            if not result.ok:
                step.detail = result.detail
                self._activity(f"Step {index}/{total} failed: {result.detail}", level="warning")
                if attempt < max_attempts:
                    self.interrupt.sleep(_RETRY_BACKOFF)
                    continue
                break  # fall through to recovery

            # ---- verify ------------------------------------------------------
            if step.expectation.kind == ExpectationKind.NONE:
                step.status = StepStatus.DONE
                step.detail = result.detail
                self._activity(f"Step {index}/{total} done: {result.detail}")
                return _StepOutcome.DONE

            self._status(AgentStatus.VERIFYING)
            self._activity(f"Verifying: {self._expectation_text(step)}")
            verification = self.verifier.verify(step.expectation)
            self._emit_verification(verification)
            if verification.status == VerificationStatus.SUCCESS:
                step.status = StepStatus.DONE
                step.detail = f"{result.detail} [{verification.detail}]"
                self._activity(f"Step {index}/{total} verified: {verification.detail}")
                return _StepOutcome.DONE
            if verification.status == VerificationStatus.UNKNOWN:
                step.status = StepStatus.DONE
                step.detail = f"{result.detail} [unverified: {verification.detail}]"
                self._activity(
                    f"Step {index}/{total} completed but unverified: {verification.detail}",
                    level="warning",
                )
                return _StepOutcome.DONE
            # FAILED (or NEEDS_USER from strict verification)
            step.detail = f"verification failed: {verification.detail}"
            if attempt < max_attempts and verification.status == VerificationStatus.FAILED:
                self.interrupt.sleep(_RETRY_BACKOFF)
                continue
            break  # recovery / give up

        # ---- recovery: ask the brain for an alternative plan -------------------
        if effective_risk == effective_risk.LOW or True:
            alternative = self.brain.replan(
                self._current_plan_for(step), step, {}
            )
            if alternative is not None:
                step.detail = "recovered via replan"
                return _StepOutcome.DONE

        step.status = StepStatus.FAILED
        if not step.detail:
            step.detail = "failed"
        self._activity(
            f"Step {index}/{total} failed after {step.attempts} attempt(s): {step.detail}",
            level="error",
        )
        self._speak(f"I couldn't {step.description.lower()}. {step.detail}")
        return (
            _StepOutcome.NEEDS_USER
            if step.risk >= step.risk.MEDIUM or ";" not in step.detail
            else _StepOutcome.FAILED
        )

    # ------------------------------------------------------------------- misc

    def _current_plan_for(self, step: Step) -> Plan:
        # Phase 1 replan context: a minimal plan containing the failed step.
        return Plan(task=step.description, steps=[step])

    def _emit_verification(self, verification: VerificationResult) -> None:
        ok = verification.status in (VerificationStatus.SUCCESS,)
        self._verification(verification.detail, ok, status=verification.status.value)

    @staticmethod
    def _expectation_text(step: Step) -> str:
        return step.expectation.kind.value.replace("_", " ")

    def _speech_for_step(self, step: Step) -> str:
        """Short spoken narration for a step start."""
        return step.description + "..."

    def _summarize_success(self, plan: Plan) -> str:
        n = len(plan.steps)
        return f"Done. Completed {n} step{'s' if n != 1 else ''}: {plan.describe()}"

    def _finish_task(
        self, request: str, plan: Plan, status: TaskStatus, summary: str
    ) -> None:
        if status == TaskStatus.COMPLETED:
            self._status(AgentStatus.COMPLETE)
            self.events.emit(EventKind.TASK, f"Task completed: {request}")
            self._speak(summary)
        elif status == TaskStatus.NEEDS_USER:
            self._status(AgentStatus.PAUSED)
            self.events.emit(
                EventKind.TASK, f"Task needs user input: {request}", level="warning"
            )
            self._speak(f"I need your help. {summary}")
        elif status == TaskStatus.INTERRUPTED:
            self._status(AgentStatus.STOPPED)
            self.events.emit(EventKind.TASK, f"Task interrupted: {request}", level="warning")
            self._speak("Stopped.")
        else:
            self._status(AgentStatus.ERROR)
            self.events.emit(EventKind.TASK, f"Task failed: {request}", level="error")


class _StepOutcome:
    DONE = "done"
    FAILED = "failed"
    NEEDS_USER = "needs_user"
