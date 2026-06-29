"""Password reset token data access repository."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.password_reset_token import PasswordResetToken


class PasswordResetTokenRepository:
    """Repository for password reset tokens."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> PasswordResetToken:
        record = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(record)
        self.db.flush()
        return record

    def get_valid_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > datetime.now(UTC),
        )
        return self.db.scalar(stmt)

    def mark_used(self, token: PasswordResetToken) -> None:
        token.used_at = datetime.now(UTC)
        self.db.add(token)

    def invalidate_all_for_user(self, user_id: uuid.UUID) -> None:
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.used_at.is_(None),
        )
        tokens = self.db.scalars(stmt).all()
        now = datetime.now(UTC)
        for token in tokens:
            token.used_at = now
            self.db.add(token)
