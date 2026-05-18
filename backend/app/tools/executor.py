from app.tools.base import ToolResult
from app.tools.registry import ToolRegistry


class ToolExecutor:
    """Execute tool calls through the registry with simple error handling."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def execute(self, tool_name: str, input_data: dict) -> ToolResult:
        if not isinstance(input_data, dict):
            return ToolResult(
                ok=False,
                content="Tool input must be an object.",
                metadata={
                    "error_type": "invalid_tool_input",
                    "tool_name": tool_name,
                    "input_type": type(input_data).__name__,
                },
            )

        tool = self.registry.get(tool_name)
        if tool is None:
            return ToolResult(
                ok=False,
                content=f"Unknown tool: {tool_name}",
                metadata={
                    "error_type": "unknown_tool",
                    "tool_name": tool_name,
                },
            )
        try:
            return tool.invoke(input_data)
        except Exception as exc:  # pragma: no cover - defensive shell
            return ToolResult(
                ok=False,
                content=str(exc),
                metadata={
                    "error_type": "tool_exception",
                    "tool_name": tool_name,
                    "exception_type": exc.__class__.__name__,
                },
            )
