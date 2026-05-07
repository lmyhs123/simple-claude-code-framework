from dataclasses import dataclass
from typing import Any, Protocol

from app.skills.registry import Skill


@dataclass(frozen=True)
class ToolCall:
    """A request from the model to call one tool."""

    name: str
    input_data: dict[str, Any]


@dataclass(frozen=True)
class ModelResponse:
    """Structured response from a model provider.

    A model can either return final text or ask the agent loop to execute one
    tool. Real providers will map vendor-specific tool-call formats into this
    project-owned shape.
    """

    text: str | None = None
    tool_call: ToolCall | None = None

    @property
    def wants_tool(self) -> bool:
        return self.tool_call is not None


class ModelProvider(Protocol):
    """Common interface for all model providers."""

    name: str

    def generate(
        self,
        *,
        messages: list[dict[str, str]],
        skill: Skill,
    ) -> ModelResponse:
        """Generate a model response from chat messages."""
