"""Supplier business logic."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.supplier import Supplier
from app.repositories.supplier_repository import SupplierRepository
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.supplier import SupplierCreate, SupplierResponse, SupplierUpdate


class SupplierService:
    """Handles supplier CRUD."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.suppliers = SupplierRepository(db)

    def create(self, payload: SupplierCreate) -> SupplierResponse:
        if self.suppliers.get_by_name(payload.supplier_name):
            raise ConflictError("A supplier with this name already exists")

        supplier = Supplier(
            supplier_name=payload.supplier_name,
            contact_person=payload.contact_person,
            email=str(payload.email) if payload.email else None,
            phone=payload.phone,
            notes=payload.notes,
            is_active=payload.is_active,
        )
        self.suppliers.create(supplier)
        self.db.commit()
        self.db.refresh(supplier)
        return SupplierResponse.model_validate(supplier)

    def get(self, supplier_id: uuid.UUID) -> SupplierResponse:
        supplier = self.suppliers.get_by_id(supplier_id)
        if not supplier:
            raise NotFoundError("Supplier not found")
        return SupplierResponse.model_validate(supplier)

    def list(self, params: PaginationParams) -> PaginatedResponse[SupplierResponse]:
        items, total = self.suppliers.list_paginated(
            page=params.page,
            page_size=params.page_size,
            search=params.search,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
        )
        return PaginatedResponse(
            items=[SupplierResponse.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=self.suppliers.total_pages(total, params.page_size),
        )

    def list_active(self) -> list[SupplierResponse]:
        return [SupplierResponse.model_validate(s) for s in self.suppliers.list_active()]

    def update(self, supplier_id: uuid.UUID, payload: SupplierUpdate) -> SupplierResponse:
        supplier = self.suppliers.get_by_id(supplier_id)
        if not supplier:
            raise NotFoundError("Supplier not found")

        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            raise ValidationError("No fields provided to update")

        if payload.supplier_name is not None:
            existing = self.suppliers.get_by_name(payload.supplier_name)
            if existing and existing.id != supplier.id:
                raise ConflictError("A supplier with this name already exists")
            supplier.supplier_name = payload.supplier_name
        if payload.contact_person is not None:
            supplier.contact_person = payload.contact_person
        if "email" in update_data:
            supplier.email = str(payload.email) if payload.email else None
        if payload.phone is not None:
            supplier.phone = payload.phone
        if payload.notes is not None:
            supplier.notes = payload.notes
        if payload.is_active is not None:
            supplier.is_active = payload.is_active

        self.db.add(supplier)
        self.db.commit()
        self.db.refresh(supplier)
        return SupplierResponse.model_validate(supplier)

    def delete(self, supplier_id: uuid.UUID) -> None:
        supplier = self.suppliers.get_by_id(supplier_id)
        if not supplier:
            raise NotFoundError("Supplier not found")
        self.suppliers.delete(supplier)
        self.db.commit()

    def ensure_exists(self, supplier_id: uuid.UUID) -> None:
        if not self.suppliers.get_by_id(supplier_id):
            raise NotFoundError("Supplier not found")
