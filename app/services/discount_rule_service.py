"""Discount rule service — CRUD + config validation."""

from __future__ import annotations

import uuid
from math import ceil

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.discount_rule import DiscountRule
from app.schemas.discount import (
    DiscountRuleCreate,
    DiscountRuleResponse,
    DiscountRuleUpdate,
    _validate_rule_config,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams


class DiscountRuleService:
    """CRUD for admin-configured discount rules."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: DiscountRuleCreate) -> DiscountRuleResponse:
        existing = self.db.scalar(
            select(DiscountRule).where(
                func.lower(DiscountRule.name) == payload.name.lower()
            )
        )
        if existing:
            raise ConflictError("A discount rule with this name already exists")

        record = DiscountRule(
            name=payload.name,
            description=payload.description,
            rule_type=payload.rule_type,
            config=payload.config,
            priority=payload.priority,
            is_active=payload.is_active,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return DiscountRuleResponse.model_validate(record)

    def get(self, rule_id: uuid.UUID) -> DiscountRuleResponse:
        return DiscountRuleResponse.model_validate(self._get_or_404(rule_id))

    def list(self, params: PaginationParams) -> PaginatedResponse[DiscountRuleResponse]:
        stmt = select(DiscountRule)
        count_stmt = select(func.count()).select_from(DiscountRule)

        if params.search:
            from app.utils.search import ilike_contains
            pattern, escape = ilike_contains(params.search)
            clause = or_(
                DiscountRule.name.ilike(pattern, escape=escape),
                DiscountRule.description.ilike(pattern, escape=escape),
            )
            stmt = stmt.where(clause)
            count_stmt = count_stmt.where(clause)

        total = int(self.db.scalar(count_stmt) or 0)
        order = asc(DiscountRule.priority) if params.sort_order == "asc" else desc(DiscountRule.priority)
        stmt = (
            stmt.order_by(order)
            .offset((params.page - 1) * params.page_size)
            .limit(params.page_size)
        )
        items = list(self.db.scalars(stmt).all())
        total_pages = ceil(total / params.page_size) if total > 0 else 0
        return PaginatedResponse(
            items=[DiscountRuleResponse.model_validate(r) for r in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    def update(self, rule_id: uuid.UUID, payload: DiscountRuleUpdate) -> DiscountRuleResponse:
        record = self._get_or_404(rule_id)
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            raise ValidationError("No fields provided to update")

        if payload.name is not None:
            existing = self.db.scalar(
                select(DiscountRule).where(
                    func.lower(DiscountRule.name) == payload.name.lower()
                )
            )
            if existing and existing.id != record.id:
                raise ConflictError("A discount rule with this name already exists")

        if payload.config is not None:
            _validate_rule_config(record.rule_type, payload.config)

        for key, value in update_data.items():
            setattr(record, key, value)

        self.db.commit()
        self.db.refresh(record)
        return DiscountRuleResponse.model_validate(record)

    def delete(self, rule_id: uuid.UUID) -> None:
        record = self._get_or_404(rule_id)
        self.db.delete(record)
        self.db.commit()

    def _get_or_404(self, rule_id: uuid.UUID) -> DiscountRule:
        record = self.db.get(DiscountRule, rule_id)
        if not record:
            raise NotFoundError("Discount rule not found")
        return record
