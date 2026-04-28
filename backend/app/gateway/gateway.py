from sqlalchemy.orm import Session

from app.memory.knowledge_service import retrieve_project_knowledge
from app.models.session import ChatSession
from app.model_providers.provider_factory import get_model_provider
from app.repositories import message_repository, project_repository
from app.gateway.context_builder import build_messages
from app.skills.registry import Skill


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
    knowledge context, skill prompt, and then calls the model provider.
    """
    project = project_repository.get_project(db, project_id)
    recent_messages = message_repository.list_recent_messages(db, session.id)
    history = [
        {"role": message.role, "content": message.content}
        for message in recent_messages
    ]

    knowledge_context = retrieve_project_knowledge(
        db=db,
        project_id=project_id,
        query=user_message,
    )

    messages = build_messages(
        skill=skill,
        user_message=user_message,
        history=history,
        project=project,
        knowledge_context=knowledge_context,
    )

    provider = get_model_provider()
    return provider.generate(messages=messages, skill=skill)
