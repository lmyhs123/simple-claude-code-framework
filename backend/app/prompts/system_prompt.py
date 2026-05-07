from app.models.project import Project
from app.skills.registry import Skill


BASE_AGENT_PROMPT = """你是 Mini Claude Code Framework 的 AI 编程助手。

你的定位：
- 你运行在一个本地项目工作台里。
- 你可以根据会话历史、项目说明、知识库片段和工具结果协助用户。
- 你优先给出清晰、稳妥、可执行的回答。
- 你不是单纯聊天机器人，而是一个能理解项目上下文的 agent。
"""


WORK_RULES_PROMPT = """工作规则：
- 先理解用户目标，再决定是否需要工具。
- 能用简单方案解决时，不要引入复杂方案。
- 如果信息不足，先说明缺口，再给出下一步建议。
- 修改代码前，应先读取相关文件并理解上下文。
- 回答尽量使用中文，除非代码、命令或专有名词需要保留英文。
"""


TOOL_RULES_PROMPT = """工具规则：
- read_file 用于读取文件内容，读取结果会包含文件的 mtime_ns。
- edit_file 用于精确替换文件内容，必须基于 read_file 返回的 mtime_ns 进行编辑。
- search_files 用于按文件名或路径搜索文件。
- search_content 用于在文本文件中搜索内容。
- write_file 用于创建或覆盖文本文件，覆盖已有文件时要谨慎。
- run_command 只能运行后端允许的安全命令。
- 工具失败不是系统崩溃，而是一次反馈；你可以根据失败原因调整下一步。
"""


def build_project_prompt(project: Project | None) -> str:
    """Build the project-specific part of the system prompt."""
    if project is None:
        return "当前项目：无\n项目说明：无\n项目自定义指令：无"

    return "\n".join(
        [
            f"当前项目：{project.name}",
            f"项目说明：{project.description or '无'}",
            f"项目自定义指令：{project.system_instruction or '无'}",
        ]
    )


def build_skill_prompt(skill: Skill) -> str:
    """Build the skill-specific part of the system prompt."""
    return "\n".join(
        [
            f"当前 skill：{skill.name}",
            f"skill 说明：{skill.description}",
            f"skill 指令：{skill.system_prompt}",
        ]
    )


def build_system_prompt(*, skill: Skill, project: Project | None = None) -> str:
    """Build the full system prompt used by the model for one turn."""
    return "\n\n".join(
        [
            BASE_AGENT_PROMPT.strip(),
            WORK_RULES_PROMPT.strip(),
            TOOL_RULES_PROMPT.strip(),
            build_project_prompt(project),
            build_skill_prompt(skill),
        ]
    )
#把所有 system prompt 片段合成最终的 system message