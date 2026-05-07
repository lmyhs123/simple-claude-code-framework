from app.model_providers.base import ModelResponse, ToolCall
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
        last_message = messages[-1] if messages else {"role": "", "content": ""}
        if last_message.get("role") == "tool":
            return ModelResponse(
                text=(
                    f"[{skill.name}] I used the requested tool and received "
                    "the following result.\n\n"
                    f"{last_message.get('content', '')}"
                )
            )

        user_message = messages[-1]["content"] if messages else ""
        history_count = max(0, len(messages) - 2)

        # Tutorial helper: type "mock_tool_read: <path>" to make the mock model
        # request one read_file tool call. Real providers will return tool calls
        # through their API instead of using this text trigger.
        if "mock_tool_read:" in user_message:
            path = user_message.split("mock_tool_read:", 1)[1].strip().splitlines()[0]
            return ModelResponse(
                tool_call=ToolCall(
                    name="read_file",
                    input_data={"path": path},
                )
            )

        if "mock_tool_search_files:" in user_message:
            query = user_message.split("mock_tool_search_files:", 1)[1].strip().splitlines()[0]
            return ModelResponse(
                tool_call=ToolCall(
                    name="search_files",
                    input_data={
                        "query": query,
                        "root": "D:/16604/course-ai-assistant",
                    },
                )
            )

        if "mock_tool_search_content:" in user_message:
            query = user_message.split("mock_tool_search_content:", 1)[1].strip().splitlines()[0]
            return ModelResponse(
                tool_call=ToolCall(
                    name="search_content",
                    input_data={
                        "query": query,
                        "root": "D:/16604/course-ai-assistant",
                    },
                )
            )

        if "mock_tool_write:" in user_message:
            payload = user_message.split("mock_tool_write:", 1)[1].strip()
            payload = payload.split("\n\n项目知识库片段：", 1)[0]
            first_line, _, rest = payload.partition("\n")
            return ModelResponse(
                tool_call=ToolCall(
                    name="write_file",
                    input_data={
                        "path": first_line.strip(),
                        "content": rest or "Created by mock write_file.",
                        "overwrite": False,
                    },
                )
            )

        if "mock_tool_edit:" in user_message:
            payload = user_message.split("mock_tool_edit:", 1)[1].strip()
            payload = payload.split("\n\n项目知识库片段：", 1)[0]
            parts = payload.split("\n---\n", 2)
            if len(parts) == 3:
                path, old_text, new_text = parts
                return ModelResponse(
                    tool_call=ToolCall(
                        name="edit_file",
                        input_data={
                            "path": path.strip(),
                            "old_text": old_text,
                            "new_text": new_text,
                        },
                    )
                )

        if "mock_tool_run:" in user_message:
            command = user_message.split("mock_tool_run:", 1)[1].strip().splitlines()[0]
            return ModelResponse(
                tool_call=ToolCall(
                    name="run_command",
                    input_data={
                        "command": command,
                        "cwd": "D:/16604/course-ai-assistant",
                    },
                )
            )

        text = (
            f"[{skill.name}] Agent loop has received this request.\n\n"
            "This is still a mock model reply, used to verify the Claude "
            "Code-like main flow before we connect a real model API.\n\n"
            f"System message received by the model:\n{system_message}\n\n"
            f"Current user message received by the model:\n{user_message}\n\n"
            f"This turn includes {history_count} historical messages."
        )
        return ModelResponse(text=text)
