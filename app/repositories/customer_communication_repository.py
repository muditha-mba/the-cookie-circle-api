"""Customer communication log data access."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.customer_communication import CustomerCommunication


class CustomerCommunicationRepository:
    """Repository for customer communication logs."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, entry: CustomerCommunication) -> CustomerCommunication:
        self.db.add(entry)
        self.db.flush()
        return self.get_by_id(entry.id)  # type: ignore[return-value]

    def get_by_id(self, entry_id: uuid.UUID) -> CustomerCommunication | None:
        stmt = (
            select(CustomerCommunication)
            .options(joinedload(CustomerCommunication.created_by))
            .where(CustomerCommunication.id == entry_id)
        )
        return self.db.scalar(stmt)

    def list_for_customer(self, customer_id: uuid.UUID) -> list[CustomerCommunication]:
        stmt = (
            select(CustomerCommunication)
            .options(joinedload(CustomerCommunication.created_by))
            .where(CustomerCommunication.customer_id == customer_id)
            .order_by(CustomerCommunication.created_at.desc())
        )
        return list(self.db.scalars(stmt).unique().all())
