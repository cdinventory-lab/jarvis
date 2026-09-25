"""Tool system (spec section 18).

Every capability JARVIS can perform is a Tool with a name, description,
parameter spec, risk level (static or computed from params), an execution
function, and - via the step's expectation - a verification method. The
registry is what the brain selects from and the orchestrator dispatches
through (after the security layer has approved).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from jarvis.security.permissions import RiskLevel


class ToolError(RuntimeError):
    """A tool failed to execute."""


class UnknownToolError(ToolError):
    """No tool with that name is registered."""


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    detail: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, str]  # param name -> human readable type/spec
    category: str  # mouse | keyboard | screen | browser | filesystem | windows | terminal
    execute: Callable[[dict[str, Any]], ToolResult] = field(repr=False)
    risk: RiskLevel = RiskLevel.LOW
    risk_for: Callable[[dict[str, Any]], RiskLevel] | None = None

    def effective_risk(self, params: dict[str, Any]) -> RiskLevel:
        if self.risk_for is not None:
            return self.risk_for(params)
        return self.risk


class ToolRegistry:
    """Registry of tools the AI can select dynamically."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool {tool.name!r} is already registered")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise UnknownToolError(f"unknown tool {name!r}") from exc

    def names(self) -> list[str]:
        return sorted(self._tools)

    def all(self) -> list[Tool]:
        return [self._tools[name] for name in sorted(self._tools)]

    def dispatch(self, name: str, params: dict[str, Any]) -> ToolResult:
        """Run a tool. ToolErrors become failed results; unexpected errors propagate."""
        tool = self.get(name)
        try:
            result = tool.execute(dict(params))
        except ToolError as exc:
            return ToolResult(ok=False, detail=str(exc))
        if not isinstance(result, ToolResult):
            return ToolResult(ok=False, detail=f"tool {name} returned invalid result")
        return result
