"""Provider-agnostic AI interface (spec section 19).

JARVIS is not coupled to any one model. Phase 1 ships a deterministic
:class:`~jarvis.core.brain.rule_brain.RuleBasedBrain` so the whole
computer-control stack works fully offline. Phase 2 wraps an LLM behind
:class:`AIProvider` (cloud or local) - the rest of JARVIS does not change.

Typical Phase-2 flow:
    provider.understand(request)      -> intents
    provider.plan(context)            -> plan
    provider.decide_action(state)     -> next tool call (agentic mode)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from jarvis.core.planner.models import Intent, Plan


class AIProvider(ABC):
    """Interface every AI backend must implement (spec section 19)."""

    #: Provider name shown in the UI ("openai", "ollama", ...).
    name: str = "abstract"

    @abstractmethod
    def understand(self, input: str, **context: Any) -> list[Intent]:
        """Turn raw user input into structured intents."""

    @abstractmethod
    def plan(self, context: dict[str, Any]) -> Plan:
        """Produce a step-by-step plan from a task context."""

    @abstractmethod
    def decide_action(self, state: dict[str, Any]) -> dict[str, Any] | None:
        """Agentic mode: choose the next single tool call, or None if done."""
