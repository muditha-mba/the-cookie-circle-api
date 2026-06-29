"""Customer business logic."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.enums import CustomerSource, UserRole
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.customer import Customer
from app.repositories.customer_repository import CustomerRepository
from app.repositories.user_repository import UserRepository
from app.schemas.customer import (
    CustomerCreate,
    CustomerDetailResponse,
    CustomerSummaryResponse,
    CustomerUpdate,
    CustomerUserSummary,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams


class CustomerService:
    """Handles customer CRUD."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.customers = CustomerRepository(db)
        self.users = UserRepository(db)

    def create(self, payload: CustomerCreate) -> CustomerDetailResponse:
        self._validate_user_link(payload.source, payload.user_id)
        if payload.user_id:
            existing = self.customers.get_by_user_id(payload.user_id)
            if existing:
                raise ConflictError("A customer profile already exists for this user")

        customer = Customer(
            user_id=payload.user_id,
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            phone=payload.phone,
            address_line_1=payload.address_line_1,
            address_line_2=payload.address_line_2,
            city=payload.city,
            postal_code=payload.postal_code,
            landmark=payload.landmark,
            source=payload.source,
            marketing_source=payload.marketing_source,
            notes=payload.notes,
            is_active=payload.is_active,
        )
        self.customers.create(customer)
        self.db.commit()
        loaded = self.customers.get_by_id(customer.id)
        assert loaded is not None
        return self._to_detail(loaded)

    def get(self, customer_id: uuid.UUID) -> CustomerDetailResponse:
        customer = self.customers.get_by_id(customer_id)
        if not customer:
            raise NotFoundError("Customer not found")
        return self._to_detail(customer)

    def list(self, params: PaginationParams) -> PaginatedResponse[CustomerSummaryResponse]:
        items, total = self.customers.list_paginated(
            page=params.page,
            page_size=params.page_size,
            search=params.search,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
        )
        return PaginatedResponse(
            items=[CustomerSummaryResponse.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=self.customers.total_pages(total, params.page_size),
        )

    def update(self, customer_id: uuid.UUID, payload: CustomerUpdate) -> CustomerDetailResponse:
        customer = self.customers.get_by_id(customer_id)
        if not customer:
            raise NotFoundError("Customer not found")

        if not payload.model_dump(exclude_unset=True):
            raise ValidationError("No fields provided to update")

        if payload.source is not None:
            user_id = payload.user_id if payload.user_id is not None else customer.user_id
            self._validate_user_link(payload.source, user_id)
            customer.source = payload.source

        if payload.user_id is not None:
            self._validate_user_link(customer.source, payload.user_id)
            existing = self.customers.get_by_user_id(payload.user_id)
            if existing and existing.id != customer.id:
                raise ConflictError("A customer profile already exists for this user")
            customer.user_id = payload.user_id

        if payload.first_name is not None:
            customer.first_name = payload.first_name
        if payload.last_name is not None:
            customer.last_name = payload.last_name
        if payload.email is not None:
            customer.email = payload.email
        if payload.phone is not None:
            customer.phone = payload.phone
        if payload.address_line_1 is not None:
            customer.address_line_1 = payload.address_line_1
        if payload.address_line_2 is not None:
            customer.address_line_2 = payload.address_line_2
        if payload.city is not None:
            customer.city = payload.city
        if payload.postal_code is not None:
            customer.postal_code = payload.postal_code
        if payload.landmark is not None:
            customer.landmark = payload.landmark
        if payload.notes is not None:
            customer.notes = payload.notes
        if "marketing_source" in payload.model_dump(exclude_unset=True):
            customer.marketing_source = payload.marketing_source
        if payload.is_active is not None:
            customer.is_active = payload.is_active

        self.db.add(customer)
        self.db.commit()
        loaded = self.customers.get_by_id(customer.id)
        assert loaded is not None
        return self._to_detail(loaded)

    def delete(self, customer_id: uuid.UUID) -> None:
        customer = self.customers.get_by_id(customer_id)
        if not customer:
            raise NotFoundError("Customer not found")
        self.customers.delete(customer)
        self.db.commit()

    def _validate_user_link(self, source: CustomerSource, user_id: uuid.UUID | None) -> None:
        if source == CustomerSource.REGISTERED:
            if user_id is None:
                raise ValidationError("Registered customers must be linked to a user")
            user = self.users.get_by_id(user_id)
            if not user:
                raise NotFoundError("User not found")
            if user.role != UserRole.CUSTOMER:
                raise ValidationError("Only customer users can be linked to a customer profile")
        elif user_id is not None:
            raise ValidationError("Only registered customers may be linked to a user")

    @staticmethod
    def _to_detail(customer: Customer) -> CustomerDetailResponse:
        user_summary = None
        if customer.user:
            user_summary = CustomerUserSummary.model_validate(customer.user)
        return CustomerDetailResponse(
            id=customer.id,
            user_id=customer.user_id,
            first_name=customer.first_name,
            last_name=customer.last_name,
            email=customer.email,
            phone=customer.phone,
            address_line_1=customer.address_line_1,
            address_line_2=customer.address_line_2,
            city=customer.city,
            postal_code=customer.postal_code,
            landmark=customer.landmark,
            source=customer.source,
            marketing_source=customer.marketing_source,
            notes=customer.notes,
            is_active=customer.is_active,
            created_at=customer.created_at,
            updated_at=customer.updated_at,
            user=user_summary,
        )
