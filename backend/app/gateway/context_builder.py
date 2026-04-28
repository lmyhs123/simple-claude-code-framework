from app.models.project import Project
from app.skills.registry import Skill


def build_messages(
    *,
    skill: Skill,
    user_message: str,
    history: list[dict[str, str]],
    project: Project | None = None,
    knowledge_context: str = "",
) -> list[dict[str, str]]:
    """Build model messages from platform state.

    This is the simplified Claude Code-like context layer:
    project instruction + skill prompt + history + knowledge + current input.
    """
    system_parts = [
        "你是 Simple Claude Code Framework 的通用 AI agent。",
        "你需要根据当前项目、会话历史、知识库片段和用户任务给出清晰、可执行的回答。",
        f"当前 skill：{skill.name}",
        skill.system_prompt,
    ]

    if project is not None:
        system_parts.extend(
            [
                "",
                f"当前项目：{project.name}",
                f"项目说明：{project.description or '无'}",
                f"项目自定义指令：{project.system_instruction or '无'}",
            ]
        )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": "\n".join(system_parts)}
    ]

    messages.extend(history)

    user_parts = ["用户问题：", user_message]
    if knowledge_context:
        user_parts.extend(["", "项目知识库片段：", knowledge_context])
    else:
        user_parts.extend(["", "项目知识库片段：当前没有检索到知识库内容。"])

    messages.append({"role": "user", "content": "\n".join(user_parts)})
    return messages
