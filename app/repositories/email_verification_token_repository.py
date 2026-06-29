"""Email verification token data access repository."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.email_verification_token import EmailVerificationToken


class EmailVerificationTokenRepository:
    """Repository for email verification tokens."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> EmailVerificationToken:
        record = EmailVerificationToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(record)
        self.db.flush()
        return record

    def get_valid_by_hash(self, token_hash: str) -> EmailVerificationToken | None:
        stmt = select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == token_hash,
            EmailVerificationToken.used_at.is_(None),
            EmailVerificationToken.expires_at > datetime.now(UTC),
        )
        return self.db.scalar(stmt)

    def mark_used(self, token: EmailVerificationToken) -> None:
        token.used_at = datetime.now(UTC)
        self.db.add(token)

    def invalidate_all_for_user(self, user_id: uuid.UUID) -> None:
        stmt = select(EmailVerificationToken).where(
            EmailVerificationToken.user_id == user_id,
            EmailVerificationToken.used_at.is_(None),
        )
        tokens = self.db.scalars(stmt).all()
        now = datetime.now(UTC)
        for token in tokens:
            token.used_at = now
            self.db.add(token)
