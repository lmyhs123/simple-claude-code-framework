from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.message import Message


def create_message(
    db: Session,
    *,
    session_id: int,
    role: str,
    content: str,
    skill_key: str | None = None,
) -> Message:
    """Create and save one message."""
    message = Message(
        session_id=session_id,
        role=role,
        content=content,
        skill_key=skill_key,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def list_messages(db: Session, session_id: int) -> list[Message]:
    """Return all messages in one session, oldest first."""
    statement = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
    )
    return list(db.scalars(statement).all())


def list_recent_messages(db: Session, session_id: int, limit: int = 10) -> list[Message]:
    """Return recent messages for building model context."""
    statement = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(limit)
    )
    messages = list(db.scalars(statement).all())
    return list(reversed(messages))
