"""Email normalization utilities."""


def normalize_email(email: str) -> str:
    """Normalize email for consistent lookup and storage."""
    return email.strip().lower()
