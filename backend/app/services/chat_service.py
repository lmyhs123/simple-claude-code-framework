from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.skills.registry import BUILTIN_SKILLS
from app.repositories import message_repository, session_repository
from app.schemas.chat import ChatRequest, ChatResponse
from app.gateway.gateway import run_gateway_turn


def send_message(db: Session, data: ChatRequest) -> ChatResponse:
    """Handle one chat turn: save user message, generate reply, save reply."""
    session = session_repository.get_session(db, data.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    skill_key = data.skill_key or session.skill_key
    skill = BUILTIN_SKILLS.get(skill_key)
    if skill is None:
        raise HTTPException(status_code=400, detail="Unknown skill")

    user_message = message_repository.create_message(
        db,
        session_id=session.id,
        role="user",
        content=data.message,
        skill_key=skill.key,
    )

    reply_text = run_gateway_turn(
        db=db,
        session=session,
        skill=skill,
        user_message=data.message,
        project_id=data.project_id,
    )

    assistant_message = message_repository.create_message(
        db,
        session_id=session.id,
        role="assistant",
        content=reply_text,
        skill_key=skill.key,
    )

    return ChatResponse(
        session_id=session.id,
        user_message=user_message,
        assistant_message=assistant_message,
    )
