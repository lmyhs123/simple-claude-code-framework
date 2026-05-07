from app.tools.base import Tool
'''
可以把它理解成:
工具目录
'''

class ToolRegistry:
    """In-memory registry for all tools available to the agent."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.definition.name in self._tools:
            raise ValueError(f"Duplicate tool registration: {tool.definition.name}")
        self._tools[tool.definition.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_definitions(self) -> list[dict]:
        return [
            {
                "name": tool.definition.name,
                "description": tool.definition.description,
                "input_schema": tool.definition.input_schema,
            }
            for tool in self._tools.values()
        ]

