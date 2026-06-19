"""Consumption proposal data access."""

import uuid
from datetime import date
from math import ceil

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.enums import ConsumptionProposalStatus, OrderStatus
from app.models.inventory_consumption_proposal import InventoryConsumptionProposal
from app.models.inventory_consumption_proposal_line import InventoryConsumptionProposalLine
from app.models.inventory_consumption_proposal_order import InventoryConsumptionProposalOrder
from app.models.order import Order
from app.models.order_collection_line import OrderCollectionLine


class ConsumptionProposalRepository:
    """Repository for consumption proposal persistence."""

    SORTABLE_COLUMNS = {
        "delivery_date": InventoryConsumptionProposal.delivery_date,
        "status": InventoryConsumptionProposal.status,
        "created_at": InventoryConsumptionProposal.created_at,
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, proposal_id: uuid.UUID) -> InventoryConsumptionProposal | None:
        stmt = (
            select(InventoryConsumptionProposal)
            .options(
                selectinload(InventoryConsumptionProposal.lines).selectinload(
                    InventoryConsumptionProposalLine.product_item,
                ),
                selectinload(InventoryConsumptionProposal.lines).selectinload(
                    InventoryConsumptionProposalLine.lot_allocations,
                ),
                selectinload(InventoryConsumptionProposal.proposal_orders).selectinload(
                    InventoryConsumptionProposalOrder.order,
                ),
            )
            .where(InventoryConsumptionProposal.id == proposal_id)
        )
        return self.db.scalar(stmt)

    def create(self, proposal: InventoryConsumptionProposal) -> InventoryConsumptionProposal:
        self.db.add(proposal)
        self.db.flush()
        return proposal

    def delete(self, proposal: InventoryConsumptionProposal) -> None:
        self.db.delete(proposal)

    def get_pending_for_delivery_date(
        self,
        delivery_date: date,
    ) -> InventoryConsumptionProposal | None:
        stmt = (
            select(InventoryConsumptionProposal)
            .where(InventoryConsumptionProposal.delivery_date == delivery_date)
            .where(InventoryConsumptionProposal.status == ConsumptionProposalStatus.PENDING_REVIEW)
        )
        return self.db.scalar(stmt)

    def count_pending(self) -> int:
        stmt = (
            select(func.count())
            .select_from(InventoryConsumptionProposal)
            .where(InventoryConsumptionProposal.status == ConsumptionProposalStatus.PENDING_REVIEW)
        )
        return int(self.db.scalar(stmt) or 0)

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
        status: ConsumptionProposalStatus | None = None,
        delivery_date: date | None = None,
    ) -> tuple[list[InventoryConsumptionProposal], int]:
        stmt = (
            select(InventoryConsumptionProposal)
            .options(
                selectinload(InventoryConsumptionProposal.lines),
                selectinload(InventoryConsumptionProposal.proposal_orders),
            )
        )
        count_stmt = select(func.count()).select_from(InventoryConsumptionProposal)

        if status is not None:
            stmt = stmt.where(InventoryConsumptionProposal.status == status)
            count_stmt = count_stmt.where(InventoryConsumptionProposal.status == status)
        if delivery_date is not None:
            stmt = stmt.where(InventoryConsumptionProposal.delivery_date == delivery_date)
            count_stmt = count_stmt.where(InventoryConsumptionProposal.delivery_date == delivery_date)

        total = int(self.db.scalar(count_stmt) or 0)
        sort_column = self.SORTABLE_COLUMNS.get(sort_by, InventoryConsumptionProposal.created_at)
        order = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        stmt = stmt.order_by(order).offset((page - 1) * page_size).limit(page_size)
        return list(self.db.scalars(stmt).all()), total

    @staticmethod
    def total_pages(total: int, page_size: int) -> int:
        if total == 0:
            return 0
        return ceil(total / page_size)

    def get_delivered_unconsumed_orders(self, delivery_date: date) -> list[Order]:
        stmt = (
            select(Order)
            .options(
                selectinload(Order.customer),
                selectinload(Order.product_lines),
                selectinload(Order.collection_lines).selectinload(
                    OrderCollectionLine.selections,
                ),
            )
            .where(Order.scheduled_delivery_date == delivery_date)
            .where(Order.status == OrderStatus.DELIVERED)
            .where(Order.inventory_consumed_at.is_(None))
            .order_by(Order.order_number.asc())
        )
        return list(self.db.scalars(stmt).unique().all())

    def get_delivered_unconsumed_orders_by_ids(self, order_ids: list[uuid.UUID]) -> list[Order]:
        if not order_ids:
            return []
        stmt = (
            select(Order)
            .options(
                selectinload(Order.customer),
                selectinload(Order.product_lines),
                selectinload(Order.collection_lines).selectinload(
                    OrderCollectionLine.selections,
                ),
            )
            .where(Order.id.in_(order_ids))
            .where(Order.status == OrderStatus.DELIVERED)
            .where(Order.inventory_consumed_at.is_(None))
            .order_by(Order.order_number.asc())
        )
        return list(self.db.scalars(stmt).unique().all())

    def order_ids_in_active_proposals(self, order_ids: list[uuid.UUID]) -> set[uuid.UUID]:
        if not order_ids:
            return set()
        stmt = (
            select(InventoryConsumptionProposalOrder.order_id)
            .join(InventoryConsumptionProposal)
            .where(InventoryConsumptionProposalOrder.order_id.in_(order_ids))
            .where(
                InventoryConsumptionProposal.status == ConsumptionProposalStatus.PENDING_REVIEW,
            )
        )
        return set(self.db.scalars(stmt).all())

    def get_pending_proposal_id_for_order(self, order_id: uuid.UUID) -> uuid.UUID | None:
        stmt = (
            select(InventoryConsumptionProposal.id)
            .join(InventoryConsumptionProposalOrder)
            .where(InventoryConsumptionProposalOrder.order_id == order_id)
            .where(InventoryConsumptionProposal.status == ConsumptionProposalStatus.PENDING_REVIEW)
        )
        return self.db.scalar(stmt)
