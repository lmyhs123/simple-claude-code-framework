from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.schemas.project import ProjectCreate


def create_project(db: Session, data: ProjectCreate) -> Project:
    """Create and save one workspace project."""
    project = Project(
        name=data.name,
        description=data.description,
        system_instruction=data.system_instruction,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def list_projects(db: Session) -> list[Project]:
    """Return projects, newest first."""
    statement = select(Project).order_by(Project.updated_at.desc())
    return list(db.scalars(statement).all())


def get_project(db: Session, project_id: int | None) -> Project | None:
    """Find one project. None means the chat is not bound to a project."""
    if project_id is None:
        return None
    return db.get(Project, project_id)
