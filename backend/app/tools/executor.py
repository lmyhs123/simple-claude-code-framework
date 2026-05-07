from app.tools.base import ToolResult
from app.tools.registry import ToolRegistry


class ToolExecutor:
    """Execute tool calls through the registry with simple error handling."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def execute(self, tool_name: str, input_data: dict) -> ToolResult:
        tool = self.registry.get(tool_name)
        if tool is None:
            return ToolResult(ok=False, content=f"Unknown tool: {tool_name}")
        try:
            return tool.invoke(input_data)
        except Exception as exc:  # pragma: no cover - defensive shell
            return ToolResult(ok=False, content=str(exc))

