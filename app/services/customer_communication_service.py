"""Customer communication log business logic."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.customer_communication import CustomerCommunication
from app.models.user import User
from app.repositories.customer_communication_repository import CustomerCommunicationRepository
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer_crm import (
    CreatedBySummary,
    CustomerCommunicationCreate,
    CustomerCommunicationResponse,
)


class CustomerCommunicationService:
    """Internal communication tracking (no outbound sending)."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.communications = CustomerCommunicationRepository(db)
        self.customers = CustomerRepository(db)

    def list_for_customer(
        self,
        customer_id: uuid.UUID,
    ) -> list[CustomerCommunicationResponse]:
        if not self.customers.get_by_id(customer_id):
            raise NotFoundError("Customer not found")
        entries = self.communications.list_for_customer(customer_id)
        return [self._to_response(entry) for entry in entries]

    def create(
        self,
        customer_id: uuid.UUID,
        payload: CustomerCommunicationCreate,
        *,
        created_by: User,
    ) -> CustomerCommunicationResponse:
        if not self.customers.get_by_id(customer_id):
            raise NotFoundError("Customer not found")

        entry = CustomerCommunication(
            customer_id=customer_id,
            communication_type=payload.communication_type,
            note=payload.note.strip(),
            created_by_id=created_by.id,
        )
        saved = self.communications.create(entry)
        self.db.commit()
        return self._to_response(saved)

    @staticmethod
    def _to_response(entry: CustomerCommunication) -> CustomerCommunicationResponse:
        return CustomerCommunicationResponse(
            id=entry.id,
            customer_id=entry.customer_id,
            communication_type=entry.communication_type,
            note=entry.note,
            created_by=CreatedBySummary.from_user(entry.created_by),
            created_at=entry.created_at,
        )
