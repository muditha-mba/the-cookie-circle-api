"""Password strength validation."""

import re

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128


def validate_password_strength(password: str) -> str:
    """Validate password meets minimum complexity requirements."""
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters",
        )
    if len(password) > PASSWORD_MAX_LENGTH:
        raise ValueError(
            f"Password must be at most {PASSWORD_MAX_LENGTH} characters",
        )
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must include a lowercase letter")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must include an uppercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must include a number")
    return password
