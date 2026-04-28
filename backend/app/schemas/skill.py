from pydantic import BaseModel


class SkillResponse(BaseModel):
    """Skill data shown to the frontend."""

    key: str
    name: str
    description: str

