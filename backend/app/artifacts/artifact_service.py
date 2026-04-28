def detect_artifact_candidate(text: str) -> bool:
    """Return whether a model response may deserve an artifact.

    Placeholder for the future artifact layer. The first real version will
    detect markdown, code blocks, and HTML output.
    """
    return "```" in text or "<html" in text.lower()

