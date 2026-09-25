"""Brain abstraction: what the orchestrator depends on.

A Brain turns text into intents and intents into a verifiable plan.
`RuleBasedBrain` (Phase 1) does this deterministically; a future
`LLMBrain` will implement the same interface on top of an AIProvider.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from jarvis.core.planner.models import Intent, Plan, Step


class Brain(ABC):
    @abstractmethod
    def understand(self, text: str) -> list[Intent]:
        """Parse natural language into one or more intents."""

    @abstractmethod
    def plan(self, intents: list[Intent], context: dict[str, Any]) -> Plan:
        """Turn intents into a plan of steps with expectations."""

    def meta_reply(self, intent_name: str) -> str | None:
        """Optional static reply for meta intents (help, greetings...)."""
        return None

    def replan(
        self,
        plan: Plan,
        failed_step: Step,
        context: dict[str, Any],
    ) -> Plan | None:
        """Error recovery (spec section 21): produce an alternative plan.

        Returning None means "no alternative - ask the user". The default
        implementation lets the orchestrator retry with the same params.
        """
        return None
