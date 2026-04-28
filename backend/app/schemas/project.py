from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Data needed to create an AI workspace project."""

    name: str = Field(default="Untitled Project", max_length=200)
    description: str | None = None
    system_instruction: str | None = None


class ProjectResponse(BaseModel):
    """Project data returned to the frontend."""

    id: int
    name: str
    description: str | None = None
    system_instruction: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
