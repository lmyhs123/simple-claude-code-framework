from fastapi import APIRouter

from app.schemas.skill import SkillResponse
from app.skills.registry import BUILTIN_SKILLS

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[SkillResponse])
def list_skills() -> list[SkillResponse]:
    """Return built-in skills for the framework."""
    return [
        SkillResponse(
            key=skill.key,
            name=skill.name,
            description=skill.description,
        )
        for skill in BUILTIN_SKILLS.values()
    ]

