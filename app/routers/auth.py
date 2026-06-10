"""Authentication routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.dependencies.auth import (
    get_auth_service,
    get_current_user,
    get_current_user_response,
)
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.auth_service import AuthService
from app.utils.captcha import verify_captcha_token
from app.utils.client_ip import get_client_ip

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegisterRequest,
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    """Register a new customer account."""
    verify_captcha_token(payload.captcha_token, remote_ip=get_client_ip(request))
    return auth_service.register(payload)


@router.post("/verify-email", response_model=UserResponse)
def verify_email(
    payload: VerifyEmailRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    """Verify a customer email address."""
    return auth_service.verify_email(payload)


@router.post("/resend-verification", response_model=MessageResponse)
def resend_verification(
    payload: ResendVerificationRequest,
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    """Resend email verification link."""
    verify_captcha_token(payload.captcha_token, remote_ip=get_client_ip(request))
    auth_service.resend_verification(payload)
    return MessageResponse(
        message="If an unverified account exists, a verification email has been sent.",
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Authenticate and receive access and refresh tokens."""
    return auth_service.login(payload, ip_address=get_client_ip(request))


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    payload: RefreshTokenRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Refresh access token using a refresh token."""
    return auth_service.refresh(payload)


@router.post("/logout", response_model=MessageResponse)
def logout(
    payload: LogoutRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    """Revoke a refresh token."""
    auth_service.logout(payload)
    return MessageResponse(message="Logged out successfully")


@router.post("/logout-all", response_model=MessageResponse)
def logout_all_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    """Revoke all refresh tokens and invalidate existing access tokens."""
    auth_service.logout_all_sessions(current_user)
    return MessageResponse(message="Logged out from all devices successfully")


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    """Request a password reset link."""
    verify_captcha_token(payload.captcha_token, remote_ip=get_client_ip(request))
    auth_service.forgot_password(payload)
    return MessageResponse(
        message="If an account exists, a password reset link has been sent.",
    )


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    payload: ResetPasswordRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    """Reset password using a reset token."""
    auth_service.reset_password(payload)
    return MessageResponse(message="Password reset successfully")


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: Annotated[UserResponse, Depends(get_current_user_response)],
) -> UserResponse:
    """Get the currently authenticated user."""
    return current_user
