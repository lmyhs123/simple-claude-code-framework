from app.models.project import Project
from app.prompts.system_prompt import build_system_prompt
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
    messages: list[dict[str, str]] = [
        {"role": "system", "content": build_system_prompt(skill=skill, project=project)}
    ]

    messages.extend(history)

    user_parts = ["用户问题：", user_message]
    if knowledge_context:
        user_parts.extend(["", "项目知识库片段：", knowledge_context])
    else:
        user_parts.extend(["", "项目知识库片段：当前没有检索到知识库内容。"])

    messages.append({"role": "user", "content": "\n".join(user_parts)})
    return messages
