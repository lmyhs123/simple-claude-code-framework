from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories import message_repository, session_repository
from app.schemas.message import MessageResponse
from app.schemas.session import SessionCreate, SessionResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(data: SessionCreate, db: Session = Depends(get_db)):
    """Create a new chat session."""
    return session_repository.create_session(db, data)


@router.get("", response_model=list[SessionResponse])
def list_sessions(db: Session = Depends(get_db)):
    """List existing chat sessions."""
    return session_repository.list_sessions(db)


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
def list_session_messages(session_id: int, db: Session = Depends(get_db)):
    """List messages for one chat session."""
    session = session_repository.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return message_repository.list_messages(db, session_id)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: int, db: Session = Depends(get_db)):
    """Soft-delete one chat session."""
    session = session_repository.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    session_repository.delete_session(db, session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

