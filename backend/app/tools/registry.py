from collections.abc import Callable

from app.tools.base import Tool, ToolDefinition
'''
可以把它理解成:
工具目录
'''

ToolFactory = Callable[[], Tool]


class ToolRegistry:
    """In-memory registry for all tools available to the agent."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._definitions: dict[str, ToolDefinition] = {}
        self._factories: dict[str, ToolFactory] = {}

    def register(self, tool: Tool) -> None:
        if tool.definition.name in self._tools or tool.definition.name in self._factories:
            raise ValueError(f"Duplicate tool registration: {tool.definition.name}")
        self._tools[tool.definition.name] = tool
        self._definitions[tool.definition.name] = tool.definition

    def register_deferred(
        self,
        definition: ToolDefinition,
        factory: ToolFactory,
    ) -> None:
        """Register a tool definition now, but create the tool only when used."""
        if definition.name in self._tools or definition.name in self._factories:
            raise ValueError(f"Duplicate tool registration: {definition.name}")
        self._definitions[definition.name] = definition
        self._factories[definition.name] = factory

    def get(self, name: str) -> Tool | None:
        tool = self._tools.get(name)
        if tool is not None:
            return tool

        factory = self._factories.get(name)
        if factory is None:
            return None

        tool = factory()
        self._tools[name] = tool
        return tool

    def list_definitions(self) -> list[dict]:
        return [
            {
                "name": definition.name,
                "description": definition.description,
                "input_schema": definition.input_schema,
            }
            for definition in self._definitions.values()
        ]
