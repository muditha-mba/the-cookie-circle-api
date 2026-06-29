"""Customer notes business logic."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.customer_note import CustomerNote
from app.models.user import User
from app.repositories.customer_note_repository import CustomerNoteRepository
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer_crm import (
    CreatedBySummary,
    CustomerNoteCreate,
    CustomerNoteResponse,
)


class CustomerNoteService:
    """Internal customer notes for staff."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.notes = CustomerNoteRepository(db)
        self.customers = CustomerRepository(db)

    def list_for_customer(self, customer_id: uuid.UUID) -> list[CustomerNoteResponse]:
        if not self.customers.get_by_id(customer_id):
            raise NotFoundError("Customer not found")
        return [self._to_response(note) for note in self.notes.list_for_customer(customer_id)]

    def create(
        self,
        customer_id: uuid.UUID,
        payload: CustomerNoteCreate,
        *,
        created_by: User,
    ) -> CustomerNoteResponse:
        if not self.customers.get_by_id(customer_id):
            raise NotFoundError("Customer not found")

        note = CustomerNote(
            customer_id=customer_id,
            note=payload.note.strip(),
            created_by_id=created_by.id,
        )
        saved = self.notes.create(note)
        self.db.commit()
        return self._to_response(saved)

    def delete(self, customer_id: uuid.UUID, note_id: uuid.UUID) -> None:
        note = self.notes.get_by_id(note_id)
        if not note or note.customer_id != customer_id:
            raise NotFoundError("Note not found")
        self.notes.delete(note)
        self.db.commit()

    @staticmethod
    def _to_response(note: CustomerNote) -> CustomerNoteResponse:
        return CustomerNoteResponse(
            id=note.id,
            customer_id=note.customer_id,
            note=note.note,
            created_by=CreatedBySummary.from_user(note.created_by),
            created_at=note.created_at,
        )
