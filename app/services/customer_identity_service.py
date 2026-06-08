"""Resolve and link customer records to authenticated users."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import CustomerSource
from app.models.customer import Customer
from app.models.order import Order
from app.models.user import User
from app.repositories.customer_repository import CustomerRepository
from app.utils.email import normalize_email


class CustomerIdentityService:
    """Keeps website orders, guest profiles, and registered accounts aligned."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.customers = CustomerRepository(db)

    def ensure_customer_for_user(self, user: User, *, commit: bool = True) -> Customer:
        """Return the canonical customer profile for an authenticated user."""
        linked = self.customers.get_by_user_id(user.id)
        email = normalize_email(user.email)
        matches = self.customers.list_by_email(email)

        if linked is not None and not any(customer.id != linked.id for customer in matches):
            return linked

        if not matches and linked is None:
            customer = Customer(
                user_id=user.id,
                first_name=user.first_name or "Customer",
                last_name=user.last_name or "",
                email=email,
                source=CustomerSource.REGISTERED,
                is_active=True,
            )
            self.customers.create(customer)
            if commit:
                self.db.commit()
                self.db.refresh(customer)
            else:
                self.db.flush()
            return customer

        candidates: dict[uuid.UUID, Customer] = {customer.id: customer for customer in matches}
        if linked is not None:
            candidates[linked.id] = linked

        canonical = self._pick_canonical_customer(user, list(candidates.values()))
        changed = canonical.user_id != user.id or canonical.source == CustomerSource.GUEST
        self._attach_user_to_customer(user, canonical)

        for other in candidates.values():
            if other.id != canonical.id and other.user_id == user.id:
                other.user_id = None
                changed = True

        if changed:
            if commit:
                self.db.commit()
                self.db.refresh(canonical)
            else:
                self.db.flush()
        return canonical

    def resolve_customer_for_checkout_email(self, email: str) -> Customer | None:
        """Find an existing customer record that should receive a new website order."""
        normalized = normalize_email(email)
        matches = self.customers.list_by_email(normalized)
        if not matches:
            return None
        return self._pick_canonical_customer_by_email(normalized, matches)

    def link_registration_to_existing_customer(self, user: User) -> Customer:
        """Attach a newly registered user to any existing guest profile with orders."""
        return self.ensure_customer_for_user(user)

    def _pick_canonical_customer(self, user: User, customers: list[Customer]) -> Customer:
        return max(
            customers,
            key=lambda customer: (
                self.customers.count_orders(customer.id) > 0,
                self.customers.count_orders(customer.id),
                customer.user_id == user.id,
                customer.created_at,
            ),
        )

    def _pick_canonical_customer_by_email(
        self,
        email: str,
        customers: list[Customer],
    ) -> Customer:
        return max(
            customers,
            key=lambda customer: (
                self.customers.count_orders(customer.id) > 0,
                self.customers.count_orders(customer.id),
                normalize_email(customer.email or "") == email,
                customer.created_at,
            ),
        )

    def _attach_user_to_customer(self, user: User, customer: Customer) -> None:
        customer.user_id = user.id
        customer.email = normalize_email(user.email)
        if customer.source == CustomerSource.GUEST:
            customer.source = CustomerSource.REGISTERED
        if not customer.first_name.strip():
            customer.first_name = user.first_name or "Customer"
        if not customer.last_name.strip():
            customer.last_name = user.last_name or ""
