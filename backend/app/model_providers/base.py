from typing import Protocol

from app.skills.registry import Skill


class ModelProvider(Protocol):
    """Common interface for all model providers."""

    name: str

    def generate(
        self,
        *,
        messages: list[dict[str, str]],
        skill: Skill,
    ) -> str:
        """Generate a model response from chat messages."""
