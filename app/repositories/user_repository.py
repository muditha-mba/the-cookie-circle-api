"""User data access repository."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import String, cast, or_, select
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.models.user import User
from app.utils.email import normalize_email


class UserRepository:
    """Repository for user persistence."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == normalize_email(email))
        return self.db.scalar(stmt)

    def list_linkable_customers(
        self,
        *,
        search: str | None,
        limit: int = 25,
    ) -> list[User]:
        """Active customer-role users available to link to a customer profile."""
        stmt = select(User).where(
            User.role == UserRole.CUSTOMER,
            User.is_active.is_(True),
        )

        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    User.email.ilike(pattern),
                    User.first_name.ilike(pattern),
                    User.last_name.ilike(pattern),
                    cast(User.id, String).ilike(pattern),
                ),
            )

        stmt = stmt.order_by(User.email.asc()).limit(limit)
        return list(self.db.scalars(stmt).all())

    def create(
        self,
        *,
        email: str,
        password_hash: str,
        role: UserRole,
        first_name: str | None = None,
        last_name: str | None = None,
        email_verified: bool = False,
    ) -> User:
        user = User(
            email=normalize_email(email),
            password_hash=password_hash,
            role=role,
            first_name=first_name,
            last_name=last_name,
            email_verified=email_verified,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def update_last_login(self, user: User) -> None:
        user.last_login_at = datetime.now(UTC)
        self.db.add(user)

    def mark_email_verified(self, user: User) -> None:
        user.email_verified = True
        self.db.add(user)

    def update_password(self, user: User, password_hash: str) -> None:
        user.password_hash = password_hash
        self.db.add(user)
