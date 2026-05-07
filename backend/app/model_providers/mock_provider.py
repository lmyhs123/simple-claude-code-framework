from app.model_providers.base import ModelResponse
from app.skills.registry import Skill


class MockModelProvider:
    """A local fake model provider used before real API integration."""

    name = "mock"

    def generate(
        self,
        *,
        messages: list[dict[str, str]],
        skill: Skill,
    ) -> ModelResponse:
        system_message = messages[0]["content"] if messages else ""
        user_message = messages[-1]["content"] if messages else ""
        history_count = max(0, len(messages) - 2)
        text = (
            f"[{skill.name}] Agent loop has received this request.\n\n"
            "This is still a mock model reply, used to verify the Claude "
            "Code-like main flow before we connect a real model API.\n\n"
            f"System message received by the model:\n{system_message}\n\n"
            f"Current user message received by the model:\n{user_message}\n\n"
            f"This turn includes {history_count} historical messages."
        )
        return ModelResponse(text=text)
