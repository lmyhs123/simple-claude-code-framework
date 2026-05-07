import httpx

from app.core.config import settings
from app.model_providers.base import ModelResponse
from app.skills.registry import Skill


class OpenAICompatibleProvider:
    """Provider for OpenAI-compatible chat completion APIs.

    This provider only handles plain text responses for now. Tool-call parsing
    will be added after the real model connection is stable.
    """

    name = "openai-compatible"

    def __init__(self) -> None:
        self.base_url = (settings.model_base_url or "https://api.openai.com/v1").rstrip("/")
        self.api_key = settings.model_api_key
        self.model_name = settings.model_name

    def generate(
        self,
        *,
        messages: list[dict[str, str]],
        skill: Skill,
    ) -> ModelResponse:
        """Generate a text response through a chat-completions style API."""
        _ = skill
        if not self.api_key:
            return ModelResponse(text="MODEL_API_KEY is not configured.")
        if not self.model_name:
            return ModelResponse(text="MODEL_NAME is not configured.")

        payload = {
            "model": self.model_name,
            "messages": self._normalize_messages(messages),
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            return ModelResponse(text=f"Model provider request failed: {exc}")

        data = response.json()
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return ModelResponse(text=f"Unexpected model response format: {data}")

        return ModelResponse(text=text or "")

    def _normalize_messages(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        """Convert framework messages into chat-completions compatible messages."""
        normalized: list[dict[str, str]] = []
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")

            # Some chat-completions-compatible providers reject role="tool"
            # unless a real tool-call id is present. Until we add full tool-call
            # support, expose tool output as a normal user-visible context block.
            if role == "tool":
                role = "user"
                content = f"Tool result:\n{content}"

            if role not in {"system", "user", "assistant"}:
                role = "user"
            normalized.append({"role": role, "content": content})
        return normalized
