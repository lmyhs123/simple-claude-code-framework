import shlex
import subprocess
from pathlib import Path

from app.core.config import settings
from app.tools.base import ToolDefinition, ToolResult

IGNORED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "data",
    "uploads",
}
TEXT_EXTENSIONS = {
    ".css",
    ".env",
    ".html",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".py",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
DEFAULT_MAX_RESULTS = 20
DEFAULT_MAX_READ_LINES = 300
COMMAND_TIMEOUT_SECONDS = 10
ALLOWED_COMMANDS = {
    ("git", "status"),
    ("git", "--version"),
    ("python", "--version"),
    ("node", "--version"),
    ("npm", "--version"),
}


def _resolve_workspace_path(raw_path: str | None) -> Path:
    workspace = settings.workspace_path
    path_value = raw_path if isinstance(raw_path, str) and raw_path.strip() else "."
    path = Path(path_value)
    if not path.is_absolute():
        path = workspace / path
    return path.resolve()


def _is_inside_workspace(path: Path) -> bool:
    try:
        path.relative_to(settings.workspace_path)
    except ValueError:
        return False
    return True


def _get_root(input_data: dict) -> tuple[Path | None, str | None]:
    root = _resolve_workspace_path(input_data.get("root"))
    if not _is_inside_workspace(root):
        return None, f"Path is outside workspace: {root}"
    return root, None


def _get_max_results(input_data: dict) -> int:
    raw_value = input_data.get("max_results", DEFAULT_MAX_RESULTS)
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        value = DEFAULT_MAX_RESULTS
    return max(1, min(value, 100))


def _get_optional_line_number(input_data: dict, key: str) -> int | None:
    raw_value = input_data.get(key)
    if raw_value is None or raw_value == "":
        return None
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None
    return max(1, value)


def _iter_project_files(root: Path):
    if not root.exists():
        return
    for path in root.rglob("*"):
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.is_file():
            yield path


def _is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS


def _get_expected_mtime_ns(input_data: dict) -> int | None:
    raw_value = input_data.get("expected_mtime_ns")
    if raw_value is None or raw_value == "":
        return None
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


class ReadFileTool:
    definition = ToolDefinition(
        name="read_file",
        description="Read one text file, optionally by line range.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read"},
                "start_line": {
                    "type": "integer",
                    "description": "1-based first line to read.",
                },
                "end_line": {
                    "type": "integer",
                    "description": "1-based last line to read.",
                },
            },
            "required": ["path"],
        },
    )

    def invoke(self, input_data: dict) -> ToolResult:
        path = input_data.get("path")
        if not isinstance(path, str) or not path.strip():
            return ToolResult(ok=False, content="input.path is required")
        file_path = _resolve_workspace_path(path)
        if not _is_inside_workspace(file_path):
            return ToolResult(ok=False, content=f"Path is outside workspace: {file_path}")
        if not file_path.exists():
            return ToolResult(ok=False, content=f"File not found: {path}")
        if not file_path.is_file():
            return ToolResult(ok=False, content=f"Path is not a file: {file_path}")
        if file_path.stat().st_size > settings.max_tool_file_size:
            return ToolResult(
                ok=False,
                content=f"File is too large to read: {file_path}",
            )
        if not _is_text_file(file_path):
            return ToolResult(ok=False, content=f"File is not a supported text file: {file_path}")
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
            total_lines = len(lines)
            start_line = _get_optional_line_number(input_data, "start_line") or 1
            end_line = _get_optional_line_number(input_data, "end_line")
            if end_line is None:
                end_line = min(total_lines, start_line + DEFAULT_MAX_READ_LINES - 1)
            if start_line > total_lines:
                return ToolResult(
                    ok=False,
                    content=f"start_line is beyond end of file: {start_line}",
                    metadata={"path": str(file_path), "total_lines": total_lines},
                )
            end_line = min(end_line, total_lines)
            if end_line < start_line:
                return ToolResult(ok=False, content="end_line must be >= start_line")

            selected_lines = lines[start_line - 1 : end_line]
            content = "\n".join(
                f"{line_number}: {line}"
                for line_number, line in enumerate(selected_lines, start=start_line)
            )
            return ToolResult(
                ok=True,
                content=content,
                metadata={
                    "path": str(file_path),
                    "mtime_ns": file_path.stat().st_mtime_ns,
                    "size": file_path.stat().st_size,
                    "start_line": start_line,
                    "end_line": end_line,
                    "total_lines": total_lines,
                },
            )
        except Exception as exc:  # pragma: no cover - simple placeholder path
            return ToolResult(ok=False, content=str(exc))


class WriteFileTool:
    definition = ToolDefinition(
        name="write_file",
        description="Write one text file inside the workspace.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
                "overwrite": {
                    "type": "boolean",
                    "description": "Whether to overwrite an existing file. Defaults to false.",
                },
            },
            "required": ["path", "content"],
        },
    )

    def invoke(self, input_data: dict) -> ToolResult:
        path = input_data.get("path")
        content = input_data.get("content")
        overwrite = input_data.get("overwrite") is True

        if not isinstance(path, str) or not path.strip():
            return ToolResult(ok=False, content="input.path is required")
        if not isinstance(content, str):
            return ToolResult(ok=False, content="input.content must be a string")
        if len(content.encode("utf-8")) > settings.max_tool_file_size:
            return ToolResult(ok=False, content="input.content is too large")

        file_path = _resolve_workspace_path(path)
        if not _is_inside_workspace(file_path):
            return ToolResult(ok=False, content=f"Path is outside workspace: {file_path}")
        if not _is_text_file(file_path):
            return ToolResult(ok=False, content=f"File is not a supported text file: {file_path}")
        if file_path.exists() and not overwrite:
            return ToolResult(
                ok=False,
                content=(
                    f"File already exists: {file_path}. "
                    "Set overwrite=true to replace it."
                ),
            )

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
        except OSError as exc:
            return ToolResult(ok=False, content=str(exc))

        return ToolResult(
            ok=True,
            content=f"Wrote file: {file_path}",
            metadata={
                "path": str(file_path),
                "bytes": len(content.encode("utf-8")),
                "overwrite": overwrite,
            },
        )


class EditFileTool:
    definition = ToolDefinition(
        name="edit_file",
        description="Edit one text file by replacing an exact text block.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_text": {
                    "type": "string",
                    "description": "Exact text to replace. Must appear exactly once.",
                },
                "new_text": {"type": "string"},
                "expected_mtime_ns": {
                    "type": "integer",
                    "description": (
                        "mtime_ns returned by read_file. "
                        "Used to prevent editing a file that changed after reading."
                    ),
                },
            },
            "required": ["path", "old_text", "new_text", "expected_mtime_ns"],
        },
    )

    def invoke(self, input_data: dict) -> ToolResult:
        path = input_data.get("path")
        old_text = input_data.get("old_text")
        new_text = input_data.get("new_text")

        if not isinstance(path, str) or not path.strip():
            return ToolResult(ok=False, content="input.path is required")
        if not isinstance(old_text, str) or old_text == "":
            return ToolResult(ok=False, content="input.old_text is required")
        if not isinstance(new_text, str):
            return ToolResult(ok=False, content="input.new_text must be a string")

        file_path = _resolve_workspace_path(path)
        if not _is_inside_workspace(file_path):
            return ToolResult(ok=False, content=f"Path is outside workspace: {file_path}")
        if not file_path.exists():
            return ToolResult(ok=False, content=f"File not found: {path}")
        if not file_path.is_file():
            return ToolResult(ok=False, content=f"Path is not a file: {file_path}")
        if file_path.stat().st_size > settings.max_tool_file_size:
            return ToolResult(ok=False, content=f"File is too large to edit: {file_path}")
        if not _is_text_file(file_path):
            return ToolResult(ok=False, content=f"File is not a supported text file: {file_path}")

        expected_mtime_ns = _get_expected_mtime_ns(input_data)
        if expected_mtime_ns is None:
            return ToolResult(
                ok=False,
                content=(
                    "expected_mtime_ns is required. "
                    "Call read_file first, then pass metadata.mtime_ns into edit_file."
                ),
            )

        current_stat = file_path.stat()
        if current_stat.st_mtime_ns != expected_mtime_ns:
            return ToolResult(
                ok=False,
                content=(
                    "File changed after it was read. "
                    "Call read_file again before editing."
                ),
                metadata={
                    "path": str(file_path),
                    "expected_mtime_ns": expected_mtime_ns,
                    "current_mtime_ns": current_stat.st_mtime_ns,
                },
            )

        try:
            original = file_path.read_text(encoding="utf-8")
        except OSError as exc:
            return ToolResult(ok=False, content=str(exc))
        except UnicodeDecodeError:
            return ToolResult(ok=False, content=f"File is not valid UTF-8 text: {file_path}")

        match_count = original.count(old_text)
        if match_count == 0:
            return ToolResult(ok=False, content="old_text was not found in file")
        if match_count > 1:
            return ToolResult(
                ok=False,
                content=f"old_text matched {match_count} times. Refusing ambiguous edit.",
            )

        updated = original.replace(old_text, new_text, 1)
        if len(updated.encode("utf-8")) > settings.max_tool_file_size:
            return ToolResult(ok=False, content="edited file would exceed max_tool_file_size")

        try:
            file_path.write_text(updated, encoding="utf-8")
        except OSError as exc:
            return ToolResult(ok=False, content=str(exc))

        return ToolResult(
            ok=True,
            content=f"Edited file: {file_path}",
            metadata={
                "path": str(file_path),
                "mtime_ns": file_path.stat().st_mtime_ns,
                "old_bytes": len(original.encode("utf-8")),
                "new_bytes": len(updated.encode("utf-8")),
            },
        )


class SearchFilesTool:
    definition = ToolDefinition(
        name="search_files",
        description="Search files by name or path substring.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "root": {
                    "type": "string",
                    "description": "Directory to search from. Defaults to current directory.",
                },
                "max_results": {"type": "integer"},
            },
            "required": ["query"],
        },
    )

    def invoke(self, input_data: dict) -> ToolResult:
        query = input_data.get("query")
        if not isinstance(query, str) or not query.strip():
            return ToolResult(ok=False, content="input.query is required")

        root, error = _get_root(input_data)
        if error is not None:
            return ToolResult(ok=False, content=error)
        assert root is not None
        if not root.exists() or not root.is_dir():
            return ToolResult(ok=False, content=f"Search root not found: {root}")

        query_lower = query.lower()
        max_results = _get_max_results(input_data)
        matches: list[str] = []

        for path in _iter_project_files(root):
            relative_path = str(path.relative_to(root))
            if query_lower in relative_path.lower():
                matches.append(relative_path)
                if len(matches) >= max_results:
                    break

        if not matches:
            return ToolResult(ok=True, content=f"No files matched query: {query}")

        return ToolResult(
            ok=True,
            content="\n".join(matches),
            metadata={"root": str(root), "count": len(matches)},
        )


class SearchContentTool:
    definition = ToolDefinition(
        name="search_content",
        description="Search text content in project files.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "root": {
                    "type": "string",
                    "description": "Directory to search from. Defaults to current directory.",
                },
                "max_results": {"type": "integer"},
            },
            "required": ["query"],
        },
    )

    def invoke(self, input_data: dict) -> ToolResult:
        query = input_data.get("query")
        if not isinstance(query, str) or not query.strip():
            return ToolResult(ok=False, content="input.query is required")

        root, error = _get_root(input_data)
        if error is not None:
            return ToolResult(ok=False, content=error)
        assert root is not None
        if not root.exists() or not root.is_dir():
            return ToolResult(ok=False, content=f"Search root not found: {root}")

        query_lower = query.lower()
        max_results = _get_max_results(input_data)
        matches: list[str] = []

        for path in _iter_project_files(root):
            if not _is_text_file(path) or path.stat().st_size > settings.max_tool_file_size:
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            except OSError as exc:
                matches.append(f"{path.relative_to(root)}: <read error: {exc}>")
                continue

            for line_number, line in enumerate(lines, start=1):
                if query_lower in line.lower():
                    snippet = line.strip()
                    relative_path = path.relative_to(root)
                    matches.append(f"{relative_path}:{line_number}: {snippet}")
                    if len(matches) >= max_results:
                        break
            if len(matches) >= max_results:
                break

        if not matches:
            return ToolResult(ok=True, content=f"No content matched query: {query}")

        return ToolResult(
            ok=True,
            content="\n".join(matches),
            metadata={"root": str(root), "count": len(matches)},
        )


class RunCommandTool:
    definition = ToolDefinition(
        name="run_command",
        description="Run one safe allowlisted command inside the workspace.",
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "cwd": {
                    "type": "string",
                    "description": "Working directory inside workspace. Defaults to workspace root.",
                },
            },
            "required": ["command"],
        },
    )

    def invoke(self, input_data: dict) -> ToolResult:
        command = input_data.get("command")
        if not isinstance(command, str) or not command.strip():
            return ToolResult(ok=False, content="input.command is required")

        try:
            args = shlex.split(command)
        except ValueError as exc:
            return ToolResult(ok=False, content=f"Invalid command: {exc}")

        if not args:
            return ToolResult(ok=False, content="input.command is empty")
        if tuple(args) not in ALLOWED_COMMANDS:
            allowed = "\n".join(" ".join(parts) for parts in sorted(ALLOWED_COMMANDS))
            return ToolResult(
                ok=False,
                content=f"Command is not allowlisted: {command}\nAllowed commands:\n{allowed}",
            )

        cwd, error = _get_root({"root": input_data.get("cwd")})
        if error is not None:
            return ToolResult(ok=False, content=error)
        assert cwd is not None
        if not cwd.exists() or not cwd.is_dir():
            return ToolResult(ok=False, content=f"cwd not found: {cwd}")

        try:
            completed = subprocess.run(
                args,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT_SECONDS,
                shell=False,
                check=False,
            )
        except FileNotFoundError:
            return ToolResult(ok=False, content=f"Command not found: {args[0]}")
        except subprocess.TimeoutExpired:
            return ToolResult(ok=False, content=f"Command timed out after {COMMAND_TIMEOUT_SECONDS}s")

        output = "\n".join(
            part
            for part in [completed.stdout.strip(), completed.stderr.strip()]
            if part
        )
        return ToolResult(
            ok=completed.returncode == 0,
            content=output or "<no output>",
            metadata={
                "command": command,
                "cwd": str(cwd),
                "returncode": completed.returncode,
            },
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


def build_builtin_tool_factories() -> list:
    """Return lazy tool factories so registry can expose tools before loading them."""
    tool_classes = [
        ReadFileTool,
        WriteFileTool,
        EditFileTool,
        SearchFilesTool,
        SearchContentTool,
        RunCommandTool,
    ]
    return [
        (tool_class.definition, tool_class)
        for tool_class in tool_classes
    ]
