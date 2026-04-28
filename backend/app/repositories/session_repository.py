from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.session import ChatSession
from app.schemas.session import SessionCreate


def create_session(db: Session, data: SessionCreate) -> ChatSession:
    """Create and save one chat session."""
    session = ChatSession(title=data.title, skill_key=data.skill_key)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def list_sessions(db: Session) -> list[ChatSession]:
    """Return non-deleted sessions, newest first."""
    statement = (
        select(ChatSession)
        .where(ChatSession.is_deleted.is_(False))
        .order_by(ChatSession.updated_at.desc())
    )
    return list(db.scalars(statement).all())


def get_session(db: Session, session_id: int) -> ChatSession | None:
    """Find one active session by id."""
    statement = select(ChatSession).where(
        ChatSession.id == session_id,
        ChatSession.is_deleted.is_(False),
    )
    return db.scalars(statement).first()


def delete_session(db: Session, session: ChatSession) -> ChatSession:
    """Soft-delete a session so its data is not lost immediately."""
    session.is_deleted = True
    db.commit()
    db.refresh(session)
    return session
