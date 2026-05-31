"""FastAPI authentication dependencies."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AuthError
from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import UserResponse
from app.services.auth_service import AuthService

bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service(db: Annotated[Session, Depends(get_db)]) -> AuthService:
    return AuthService(db)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthError("Not authenticated")

    try:
        payload = decode_access_token(credentials.credentials)
    except Exception as exc:
        raise AuthError("Invalid or expired access token") from exc

    if payload.get("type") != "access":
        raise AuthError("Invalid token type")

    subject = payload.get("sub")
    if not subject:
        raise AuthError("Invalid token payload")

    return auth_service.get_current_user(subject)


def get_current_user_response(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    return UserResponse.model_validate(current_user)
