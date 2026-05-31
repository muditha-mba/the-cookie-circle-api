"""Authentication business logic."""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.core.enums import AppContext, UserRole
from app.core.exceptions import AuthError, ConflictError, ForbiddenError, ValidationError
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.email_verification_token_repository import (
    EmailVerificationTokenRepository,
)
from app.repositories.password_reset_token_repository import PasswordResetTokenRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.email import get_email_service
from app.utils.tokens import generate_secure_token, hash_token


class AuthService:
    """Handles authentication flows."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)
        self.email_tokens = EmailVerificationTokenRepository(db)
        self.password_tokens = PasswordResetTokenRepository(db)
        self.email_service = get_email_service()

    def register(self, payload: RegisterRequest) -> UserResponse:
        if self.users.get_by_email(payload.email):
            raise ConflictError("An account with this email already exists")

        user = self.users.create(
            email=payload.email,
            password_hash=hash_password(payload.password),
            role=UserRole.CUSTOMER,
            first_name=payload.first_name,
            last_name=payload.last_name,
            email_verified=False,
        )
        self._issue_verification_token(user)
        self.db.commit()
        self.db.refresh(user)
        return UserResponse.model_validate(user)

    def verify_email(self, payload: VerifyEmailRequest) -> UserResponse:
        token_record = self.email_tokens.get_valid_by_hash(hash_token(payload.token))
        if not token_record:
            raise ValidationError("Invalid or expired verification token")

        user = token_record.user
        self.email_tokens.mark_used(token_record)
        self.users.mark_email_verified(user)
        self.db.commit()
        self.db.refresh(user)
        return UserResponse.model_validate(user)

    def resend_verification(self, payload: ResendVerificationRequest) -> None:
        user = self.users.get_by_email(payload.email)
        if not user:
            return
        if user.email_verified:
            return
        if user.role != UserRole.CUSTOMER:
            return

        self.email_tokens.invalidate_all_for_user(user.id)
        self._issue_verification_token(user)
        self.db.commit()

    def login(self, payload: LoginRequest) -> TokenResponse:
        user = self.users.get_by_email(payload.email)
        if not user or not verify_password(payload.password, user.password_hash):
            raise AuthError("Invalid email or password")

        if not user.is_active:
            raise ForbiddenError("Account is inactive")

        if payload.app == AppContext.ADMIN and user.role != UserRole.ADMIN:
            raise ForbiddenError("Admin access required")

        if payload.app == AppContext.CLIENT and user.role != UserRole.CUSTOMER:
            raise ForbiddenError("Customer access required")

        if user.role == UserRole.CUSTOMER and not user.email_verified:
            raise ForbiddenError("Email verification required")

        self.users.update_last_login(user)
        tokens = self._issue_tokens(user)
        self.db.commit()
        self.db.refresh(user)
        return TokenResponse(
            **tokens,
            user=UserResponse.model_validate(user),
        )

    def refresh(self, payload: RefreshTokenRequest) -> TokenResponse:
        token_hash = hash_token(payload.refresh_token)
        token_record = self.refresh_tokens.get_by_hash(token_hash)
        if not token_record:
            raise AuthError("Invalid or expired refresh token")

        if token_record.revoked_at is not None:
            logger.warning(
                "Refresh token reuse detected for user_id=%s",
                token_record.user_id,
            )
            self.refresh_tokens.revoke_all_for_user(token_record.user_id)
            self.db.commit()
            raise AuthError("Invalid or expired refresh token")

        if token_record.expires_at <= datetime.now(UTC):
            raise AuthError("Invalid or expired refresh token")

        user = token_record.user
        if not user.is_active:
            raise ForbiddenError("Account is inactive")

        self.refresh_tokens.revoke(token_record)
        tokens = self._issue_tokens(user)
        self.db.commit()
        self.db.refresh(user)
        return TokenResponse(
            **tokens,
            user=UserResponse.model_validate(user),
        )

    def logout(self, payload: LogoutRequest) -> None:
        token_record = self.refresh_tokens.get_valid_by_hash(
            hash_token(payload.refresh_token),
        )
        if token_record:
            self.refresh_tokens.revoke(token_record)
            self.db.commit()

    def forgot_password(self, payload: ForgotPasswordRequest) -> None:
        user = self.users.get_by_email(payload.email)
        if not user or not user.is_active:
            return

        self.password_tokens.invalidate_all_for_user(user.id)
        raw_token = generate_secure_token()
        expires_at = datetime.now(UTC) + timedelta(
            hours=settings.password_reset_token_expire_hours,
        )
        self.password_tokens.create(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=expires_at,
        )

        if user.role == UserRole.ADMIN:
            reset_url = (
                f"{settings.frontend_admin_url}/reset-password?token={raw_token}"
            )
        else:
            reset_url = (
                f"{settings.frontend_client_url}/reset-password?token={raw_token}"
            )

        self.email_service.send_password_reset_email(
            to_email=user.email,
            reset_url=reset_url,
        )
        self.db.commit()

    def reset_password(self, payload: ResetPasswordRequest) -> None:
        token_record = self.password_tokens.get_valid_by_hash(
            hash_token(payload.token),
        )
        if not token_record:
            raise ValidationError("Invalid or expired reset token")

        user = token_record.user
        self.password_tokens.mark_used(token_record)
        self.users.update_password(user, hash_password(payload.password))
        self.refresh_tokens.revoke_all_for_user(user.id)
        self.db.commit()

    def get_current_user(self, user_id: str) -> User:
        from uuid import UUID

        user = self.users.get_by_id(UUID(user_id))
        if not user or not user.is_active:
            raise AuthError("Invalid or inactive user")
        return user

    def _issue_tokens(self, user: User) -> dict[str, str]:
        access_token = create_access_token(subject=user.id, role=user.role.value)
        raw_refresh = generate_secure_token()
        expires_at = datetime.now(UTC) + timedelta(
            days=settings.refresh_token_expire_days,
        )
        self.refresh_tokens.create(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            expires_at=expires_at,
        )
        return {
            "access_token": access_token,
            "refresh_token": raw_refresh,
        }

    def _issue_verification_token(self, user: User) -> None:
        raw_token = generate_secure_token()
        expires_at = datetime.now(UTC) + timedelta(
            hours=settings.email_verification_token_expire_hours,
        )
        self.email_tokens.create(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=expires_at,
        )
        verification_url = (
            f"{settings.frontend_client_url}/verify-email?token={raw_token}"
        )
        self.email_service.send_verification_email(
            to_email=user.email,
            verification_url=verification_url,
        )
