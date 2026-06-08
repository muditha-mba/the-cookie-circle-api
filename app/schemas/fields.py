"""Shared Pydantic field types for authentication schemas."""

from typing import Annotated

from pydantic import BeforeValidator, EmailStr

from app.utils.email import normalize_email

NormalizedEmail = Annotated[
    EmailStr,
    BeforeValidator(lambda value: normalize_email(value) if isinstance(value, str) else value),
]
