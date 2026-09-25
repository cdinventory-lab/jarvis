"""Permission / safety layer (spec section 15).

Every action JARVIS takes goes through :class:`SecurityPolicy` first:

* LOW risk    - open an app, search the web, scroll, read, type ordinary
                text. Executes automatically.
* MEDIUM risk - download, modify files, install, send, change settings.
                Asks for confirmation depending on configuration.
* HIGH risk   - mass deletion, security/system settings, unknown admin
                commands, irreversible actions. Always asks.

The policy never silently bypasses OS security boundaries: anything the OS
would block still gets blocked by the OS. This layer exists so JARVIS does
not *attempt* dangerous things without explicit user consent.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoids a circular import: core depends on security
    from jarvis.core.events import EventBus


class RiskLevel(IntEnum):
    """How dangerous an action is. Higher = more dangerous."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3

    @property
    def label(self) -> str:
        return {RiskLevel.LOW: "low", RiskLevel.MEDIUM: "medium", RiskLevel.HIGH: "high"}[self]

    @classmethod
    def parse(cls, value: str) -> RiskLevel:
        try:
            return cls[value.strip().upper()]
        except KeyError as exc:
            raise ValueError(
                f"unknown risk level {value!r} (expected low/medium/high)"
            ) from exc


class SecurityError(RuntimeError):
    """Raised when an action is refused by the safety layer."""


@dataclass(frozen=True)
class PermissionRequest:
    """A request to perform one concrete action."""

    tool: str
    action: str
    risk: RiskLevel
    params: Mapping[str, object]


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    reason: str
    asked_user: bool = False


class Approver(ABC):
    """Interactive confirmation source (UI prompt, dialog, voice yes/no...)."""

    @abstractmethod
    def ask(self, request: PermissionRequest) -> bool: ...


class DenyAllApprover(Approver):
    """Safe default for non-interactive runs: deny anything that asks."""

    def ask(self, request: PermissionRequest) -> bool:
        return False


class AutoApprover(Approver):
    """Approves everything - tests and explicit `--assume-yes` runs only."""

    def ask(self, request: PermissionRequest) -> bool:
        return True


class SecurityPolicy:
    """Decides whether an action may run, and whether the user must confirm.

    Rules (in order):
      1. risk <= auto_approve_risk            -> allowed, no question.
      2. risk <= MEDIUM and assume_yes is on  -> allowed (explicit opt-in
         for scripted demos; HIGH still asks).
      3. otherwise                            -> ask the approver.
    """

    def __init__(
        self,
        auto_approve_risk: RiskLevel = RiskLevel.LOW,
        assume_yes: bool = False,
        approver: Approver | None = None,
        events: EventBus | None = None,
    ) -> None:
        self.auto_approve_risk = auto_approve_risk
        self.assume_yes = assume_yes
        self.approver = approver
        self.events = events

    def check(self, request: PermissionRequest) -> PermissionDecision:
        if request.risk <= self.auto_approve_risk:
            decision = PermissionDecision(
                allowed=True, reason=f"{request.risk.label} risk: auto-approved"
            )
            self._notify(request, decision)
            return decision
        if self.assume_yes and request.risk <= RiskLevel.MEDIUM:
            decision = PermissionDecision(
                allowed=True, reason="auto-approved (--assume-yes)", asked_user=False
            )
            self._notify(request, decision)
            return decision

        approver = self.approver or DenyAllApprover()
        approved = approver.ask(request)
        decision = PermissionDecision(
            allowed=approved,
            reason="user approved" if approved else "user denied",
            asked_user=True,
        )
        self._notify(request, decision)
        return decision

    def _notify(self, request: PermissionRequest, decision: PermissionDecision) -> None:
        if self.events is None:
            return
        if request.risk <= RiskLevel.LOW and not decision.asked_user:
            return  # low-risk auto-approvals would spam the activity feed
        # Duck-typed on purpose: the bus accepts string event kinds.
        self.events.emit(
            "approval",
            (
                f"Approved: {request.action} ({decision.reason})"
                if decision.allowed
                else f"Denied: {request.action} ({decision.reason})"
            ),
            level="info" if decision.allowed else "warning",
            tool=request.tool,
            risk=request.risk.label,
        )
