from datetime import datetime

from pydantic import BaseModel


class MessageResponse(BaseModel):
    """A chat message returned to the frontend."""

    id: int
    session_id: int
    role: str
    content: str
    skill_key: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
