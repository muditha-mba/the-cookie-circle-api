"""Customer saved address repository."""

import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.customer_address import CustomerAddress


class CustomerAddressRepository:
    """Persistence for customer address book entries."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_customer(self, customer_id: uuid.UUID) -> list[CustomerAddress]:
        stmt = (
            select(CustomerAddress)
            .where(CustomerAddress.customer_id == customer_id)
            .order_by(
                CustomerAddress.is_default.desc(),
                CustomerAddress.created_at.desc(),
            )
        )
        return list(self.db.scalars(stmt).all())

    def get_by_id(self, address_id: uuid.UUID) -> CustomerAddress | None:
        return self.db.get(CustomerAddress, address_id)

    def get_default(self, customer_id: uuid.UUID) -> CustomerAddress | None:
        stmt = select(CustomerAddress).where(
            CustomerAddress.customer_id == customer_id,
            CustomerAddress.is_default.is_(True),
        )
        return self.db.scalar(stmt)

    def create(self, address: CustomerAddress) -> CustomerAddress:
        self.db.add(address)
        self.db.flush()
        return address

    def delete(self, address: CustomerAddress) -> None:
        self.db.delete(address)

    def clear_default(self, customer_id: uuid.UUID) -> None:
        stmt = (
            update(CustomerAddress)
            .where(CustomerAddress.customer_id == customer_id)
            .values(is_default=False)
        )
        self.db.execute(stmt)
