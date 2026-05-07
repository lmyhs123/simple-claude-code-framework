from pathlib import Path

from app.tools.base import ToolDefinition, ToolResult


class ReadFileTool:
    definition = ToolDefinition(
        name="read_file",
        description="Read the content of one text file.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read"},
            },
            "required": ["path"],
        },
    )

    def invoke(self, input_data: dict) -> ToolResult:
        path = input_data.get("path")
        if not isinstance(path, str) or not path.strip():
            return ToolResult(ok=False, content="input.path is required")
        file_path = Path(path)
        if not file_path.exists():
            return ToolResult(ok=False, content=f"File not found: {path}")
        try:
            return ToolResult(ok=True, content=file_path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - simple placeholder path
            return ToolResult(ok=False, content=str(exc))


class WriteFileTool:
    definition = ToolDefinition(
        name="write_file",
        description="Placeholder tool for writing one file.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    )

    def invoke(self, input_data: dict) -> ToolResult:
        _ = input_data
        return ToolResult(
            ok=False,
            content="write_file is not implemented yet in the framework skeleton.",
        )


class EditFileTool:
    definition = ToolDefinition(
        name="edit_file",
        description="Placeholder tool for patch-like file edits.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "instruction": {"type": "string"},
            },
            "required": ["path", "instruction"],
        },
    )

    def invoke(self, input_data: dict) -> ToolResult:
        _ = input_data
        return ToolResult(
            ok=False,
            content="edit_file is not implemented yet in the framework skeleton.",
        )


class SearchFilesTool:
    definition = ToolDefinition(
        name="search_files",
        description="Placeholder tool for searching files by name or pattern.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
        },
    )

    def invoke(self, input_data: dict) -> ToolResult:
        _ = input_data
        return ToolResult(
            ok=False,
            content="search_files is not implemented yet in the framework skeleton.",
        )


class SearchContentTool:
    definition = ToolDefinition(
        name="search_content",
        description="Placeholder tool for searching code or text content.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
        },
    )

    def invoke(self, input_data: dict) -> ToolResult:
        _ = input_data
        return ToolResult(
            ok=False,
            content="search_content is not implemented yet in the framework skeleton.",
        )


class RunCommandTool:
    definition = ToolDefinition(
        name="run_command",
        description="Placeholder tool for shell command execution.",
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string"},
            },
            "required": ["command"],
        },
    )

    def invoke(self, input_data: dict) -> ToolResult:
        _ = input_data
        return ToolResult(
            ok=False,
            content="run_command is not implemented yet in the framework skeleton.",
        )


def build_builtin_tools() -> list:
    """Return the six core tools from the tutorial as framework placeholders."""
    return [
        ReadFileTool(),
        WriteFileTool(),
        EditFileTool(),
        SearchFilesTool(),
        SearchContentTool(),
        RunCommandTool(),
    ]

