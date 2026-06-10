"""Authentication Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.enums import AdminRole, AppContext, UserRole
from app.schemas.attribution import MarketingAttributionInput
from app.schemas.fields import NormalizedEmail
from app.utils.password import validate_password_strength


class RegisterRequest(BaseModel):
    """Customer registration request."""

    email: NormalizedEmail
    password: str = Field(min_length=8, max_length=128)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    captcha_token: str | None = Field(default=None, max_length=4096)
    attribution: MarketingAttributionInput | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)


class LoginRequest(BaseModel):
    """Login request."""

    email: NormalizedEmail
    password: str = Field(min_length=1, max_length=128)
    app: AppContext | None = Field(
        default=None,
        description="Restrict login to admin or client application context",
    )


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str = Field(min_length=1)


class VerifyEmailRequest(BaseModel):
    """Email verification request."""

    token: str = Field(min_length=1)
    email: NormalizedEmail | None = Field(
        default=None,
        description="Required when using the development verification token",
    )


class ResendVerificationRequest(BaseModel):
    """Resend verification email request."""

    email: NormalizedEmail
    captcha_token: str | None = Field(default=None, max_length=4096)


class ForgotPasswordRequest(BaseModel):
    """Forgot password request."""

    email: NormalizedEmail
    captcha_token: str | None = Field(default=None, max_length=4096)


class ResetPasswordRequest(BaseModel):
    """Reset password request."""

    token: str = Field(min_length=1)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)


class LogoutRequest(BaseModel):
    """Logout request."""

    refresh_token: str = Field(min_length=1)


class UserResponse(BaseModel):
    """Public user response."""

    id: UUID
    email: EmailStr
    role: UserRole
    admin_role: AdminRole | None = None
    first_name: str | None
    last_name: str | None
    email_verified: bool
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Authentication token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
