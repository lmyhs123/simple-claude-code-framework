import json

import httpx

from app.core.config import settings
from app.model_providers.base import ModelResponse, ToolCall
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
        tools: list[dict] | None = None,
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
        normalized_tools = self._normalize_tools(tools or [])
        if normalized_tools:
            payload["tools"] = normalized_tools
            payload["tool_choice"] = "auto"

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

        return self._parse_response(response.json())

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

    def _normalize_tools(self, tools: list[dict]) -> list[dict]:
        """Convert framework tool definitions into OpenAI-compatible tools."""
        normalized: list[dict] = []
        for tool in tools:
            name = tool.get("name")
            description = tool.get("description", "")
            input_schema = tool.get("input_schema", {"type": "object", "properties": {}})
            if not isinstance(name, str) or not name:
                continue
            normalized.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": description,
                        "parameters": input_schema,
                    },
                }
            )
        return normalized

    def _parse_response(self, data: dict) -> ModelResponse:
        """Convert an OpenAI-compatible response into this framework's shape."""
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError):
            return ModelResponse(text=f"Unexpected model response format: {data}")

        tool_calls = message.get("tool_calls") or []
        if tool_calls:
            tool_call = self._parse_first_tool_call(tool_calls)
            if tool_call is not None:
                return ModelResponse(tool_call=tool_call)

        content = message.get("content")
        if content is None:
            content = ""
        return ModelResponse(text=str(content))

    def _parse_first_tool_call(self, tool_calls: list[dict]) -> ToolCall | None:
        """Parse the first tool call returned by a compatible chat API."""
        first_call = tool_calls[0] if tool_calls else None
        if not isinstance(first_call, dict):
            return None

        function = first_call.get("function") or {}
        name = function.get("name")
        raw_arguments = function.get("arguments") or "{}"
        if not isinstance(name, str) or not name:
            return None

        try:
            input_data = json.loads(raw_arguments)
        except json.JSONDecodeError:
            input_data = {"raw_arguments": raw_arguments}

        if not isinstance(input_data, dict):
            input_data = {"value": input_data}

        return ToolCall(name=name, input_data=input_data)
