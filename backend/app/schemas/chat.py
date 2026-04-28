from pydantic import BaseModel, Field

from app.schemas.message import MessageResponse


class ChatRequest(BaseModel):
    """Request body for sending one user message."""

    session_id: int
    message: str = Field(min_length=1)
    skill_key: str | None = None
    project_id: int | None = None


class ChatResponse(BaseModel):
    """Response body after the assistant generates a reply."""

    session_id: int
    user_message: MessageResponse
    assistant_message: MessageResponse
