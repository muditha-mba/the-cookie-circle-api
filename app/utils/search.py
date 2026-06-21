"""Search pattern helpers for safe SQL ILIKE usage."""


def escape_ilike(value: str) -> str:
    """Escape PostgreSQL ILIKE wildcard characters."""
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def ilike_contains(term: str) -> tuple[str, str]:
    """Build a case-insensitive contains pattern with escape metadata."""
    stripped = term.strip()
    if not stripped:
        return "%", "\\"
    return f"%{escape_ilike(stripped)}%", "\\"
