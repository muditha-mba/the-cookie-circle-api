"""Admin user lookup for customer linking."""

from sqlalchemy.orm import Session

from uuid import UUID

from app.core.enums import UserRole
from app.core.exceptions import NotFoundError
from app.repositories.user_repository import UserRepository
from app.schemas.user import LinkableUserListResponse, LinkableUserResponse


def _display_name(user) -> str:
    parts = [user.first_name, user.last_name]
    name = " ".join(part for part in parts if part).strip()
    return name or user.email


class UserLookupService:
    """Search users that can be linked to customer records."""

    def __init__(self, db: Session) -> None:
        self.users = UserRepository(db)

    def list_linkable_customers(
        self,
        *,
        search: str | None,
        limit: int,
    ) -> LinkableUserListResponse:
        users = self.users.list_linkable_customers(search=search, limit=limit)
        return LinkableUserListResponse(
            items=[self._to_response(user) for user in users],
        )

    def get_linkable_customer(self, user_id: UUID) -> LinkableUserResponse:
        user = self.users.get_by_id(user_id)
        if not user or user.role != UserRole.CUSTOMER:
            raise NotFoundError("User not found")
        if not user.is_active:
            raise NotFoundError("User is inactive")
        return self._to_response(user)

    @staticmethod
    def _to_response(user) -> LinkableUserResponse:
        return LinkableUserResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            display_name=_display_name(user),
        )
