"""Customer saved address management."""

import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.customer import Customer
from app.models.customer_address import CustomerAddress
from app.repositories.customer_address_repository import CustomerAddressRepository
from app.schemas.client_account import (
    ClientAccountAddressCreate,
    ClientAccountAddressResponse,
    ClientAccountAddressUpdate,
)


class ClientAddressService:
    """CRUD for customer address book."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.addresses = CustomerAddressRepository(db)

    def list_addresses(self, customer: Customer) -> list[ClientAccountAddressResponse]:
        rows = self.addresses.list_for_customer(customer.id)
        return [ClientAccountAddressResponse.model_validate(row) for row in rows]

    def create_address(
        self,
        customer: Customer,
        payload: ClientAccountAddressCreate,
    ) -> ClientAccountAddressResponse:
        existing = self.addresses.list_for_customer(customer.id)
        is_first = len(existing) == 0
        if payload.is_default or is_first:
            self.addresses.clear_default(customer.id)

        address = CustomerAddress(
            customer_id=customer.id,
            label=payload.label.strip(),
            recipient_name=payload.recipient_name.strip(),
            phone=payload.phone.strip(),
            address_line_1=payload.address_line_1.strip(),
            address_line_2=payload.address_line_2,
            city=payload.city.strip(),
            postal_code=payload.postal_code,
            landmark=payload.landmark,
            latitude=payload.latitude,
            longitude=payload.longitude,
            is_default=payload.is_default or is_first,
        )
        self.addresses.create(address)
        self.db.commit()
        self.db.refresh(address)
        return ClientAccountAddressResponse.model_validate(address)

    def update_address(
        self,
        customer: Customer,
        address_id: uuid.UUID,
        payload: ClientAccountAddressUpdate,
    ) -> ClientAccountAddressResponse:
        address = self._get_owned_address(customer, address_id)
        data = payload.model_dump(exclude_unset=True)
        if data.get("is_default"):
            self.addresses.clear_default(customer.id)
        for field, value in data.items():
            if field in {"label", "recipient_name", "phone", "address_line_1", "city"} and isinstance(
                value,
                str,
            ):
                value = value.strip()
            setattr(address, field, value)
        self.db.commit()
        self.db.refresh(address)
        return ClientAccountAddressResponse.model_validate(address)

    def delete_address(self, customer: Customer, address_id: uuid.UUID) -> None:
        address = self._get_owned_address(customer, address_id)
        was_default = address.is_default
        self.addresses.delete(address)
        self.db.flush()
        if was_default:
            remaining = self.addresses.list_for_customer(customer.id)
            if remaining:
                remaining[0].is_default = True
        self.db.commit()

    def set_default(self, customer: Customer, address_id: uuid.UUID) -> ClientAccountAddressResponse:
        address = self._get_owned_address(customer, address_id)
        self.addresses.clear_default(customer.id)
        address.is_default = True
        self.db.commit()
        self.db.refresh(address)
        return ClientAccountAddressResponse.model_validate(address)

    def _get_owned_address(self, customer: Customer, address_id: uuid.UUID) -> CustomerAddress:
        address = self.addresses.get_by_id(address_id)
        if not address or address.customer_id != customer.id:
            raise NotFoundError("Address not found")
        return address
