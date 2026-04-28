from datetime import datetime

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    """Data needed to create a new chat session."""

    title: str = Field(default="新会话", max_length=200)
    skill_key: str = "general"


class SessionResponse(BaseModel):
    """Session data returned to the frontend."""

    id: int
    title: str
    skill_key: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
