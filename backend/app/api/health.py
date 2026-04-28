from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Return a small response so we know the backend is alive."""
    return {"status": "ok", "service": "simple-claude-code-framework"}
