from sqlalchemy.orm import Session


def retrieve_project_knowledge(
    *,
    db: Session,
    project_id: int | None,
    query: str,
) -> str:
    """Return knowledge snippets for a project.

    This placeholder keeps the architecture explicit. The next implementation
    will search document_chunks by project_id and query keywords.
    """
    _ = db, project_id, query
    return ""

