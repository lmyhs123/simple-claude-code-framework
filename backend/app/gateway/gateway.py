from sqlalchemy.orm import Session

from app.agent.loop import AgentLoop
from app.gateway.context_builder import build_messages
from app.memory.knowledge_service import retrieve_project_knowledge
from app.model_providers.provider_factory import get_model_provider
from app.models.session import ChatSession
from app.repositories import message_repository, project_repository
from app.skills.registry import Skill
from app.tools.builtin_tools import build_builtin_tools
from app.tools.registry import ToolRegistry

# 这个文件是“总调度层”。
# 它不负责真正的工具循环，而是负责把一轮 AI 请求需要的材料准备齐：
# - project
# - 历史消息
# - knowledge context
# - skill prompt
# - tools
# 然后交给 AgentLoop。

def run_gateway_turn(
    *,
    db: Session,
    session: ChatSession,
    skill: Skill,
    user_message: str,
    project_id: int | None = None,
) -> str:
    """Coordinate one AI turn.

    Gateway is the platform brain: it gathers session history, project data,
    knowledge context, skill prompt, and then hands the request to the agent
    loop.
    """
    # 先拿到当前 project。Claude Code-like 系统不是“真空聊天”，
    # 而是在某个 project / workspace 里工作。
    project = project_repository.get_project(db, project_id)

    # 读取最近的会话历史，再转成模型能直接使用的消息格式。
    recent_messages = message_repository.list_recent_messages(db, session.id)
    history = [
        {"role": message.role, "content": message.content}
        for message in recent_messages
    ]

    # 这里是 memory / knowledge 的入口。
    # 用户问题进来后，先尝试从当前 project 的知识里找相关内容。
    knowledge_context = retrieve_project_knowledge(
        db=db,
        project_id=project_id,
        query=user_message,
    )

    # 把 skill、project、history、knowledge、当前用户输入合成最终 messages。
    # 真正决定模型“看到什么”的关键就在这里。
    messages = build_messages(
        skill=skill,
        user_message=user_message,
        history=history,
        project=project,
        knowledge_context=knowledge_context,
    )

    # 注册本轮可用工具。
    # 现在只是骨架，但已经和教程第一章的方向对齐了。
    tool_registry = ToolRegistry()
    for tool in build_builtin_tools():
        tool_registry.register(tool)

    # gateway 不直接生成最终答案，而是把 provider 和 messages 交给 loop。
    provider = get_model_provider()
    loop = AgentLoop(tool_registry)
    result = loop.run(messages=messages, provider=provider, skill=skill)
    return result.final_text
