"""Consumption proposal business logic."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.enums import (
    ActivityAction,
    ActivityResourceType,
    ConsumptionProposalStatus,
)
from app.core.exceptions import NotFoundError, ValidationError
from app.models.inventory_consumption_proposal import InventoryConsumptionProposal
from app.models.inventory_consumption_proposal_line import InventoryConsumptionProposalLine
from app.models.inventory_consumption_proposal_lot_allocation import (
    InventoryConsumptionProposalLotAllocation,
)
from app.models.inventory_consumption_proposal_order import InventoryConsumptionProposalOrder
from app.models.order import Order
from app.repositories.consumption_proposal_repository import ConsumptionProposalRepository
from app.schemas.consumption_proposal import (
    ConsumptionProposalGenerateRequest,
    ConsumptionProposalLineResponse,
    ConsumptionProposalLotAllocationResponse,
    ConsumptionProposalOrderSummary,
    ConsumptionProposalPendingCount,
    ConsumptionProposalResponse,
    ConsumptionProposalSummary,
    ConsumptionProposalUpdate,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.services.activity_log_service import ActivityLogService
from app.services.consumption_demand_service import ConsumptionDemandService
from app.services.fefo_allocation_service import FefoAllocationService
from app.services.inventory_balance_service import InventoryBalanceService
from app.services.inventory_movement_service import InventoryMovementService

QTY_PRECISION = Decimal("0.0001")


class ConsumptionProposalService:
    """Generate, review, approve, and dismiss consumption proposals."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.proposals = ConsumptionProposalRepository(db)
        self.demand = ConsumptionDemandService(db)
        self.fefo = FefoAllocationService(db)
        self.balances = InventoryBalanceService(db)
        self.movements = InventoryMovementService(db)
        self.activity = ActivityLogService(db)

    def list(
        self,
        params: PaginationParams,
        *,
        status: ConsumptionProposalStatus | None = None,
        delivery_date: date | None = None,
    ) -> PaginatedResponse[ConsumptionProposalSummary]:
        rows, total = self.proposals.list_paginated(
            page=params.page,
            page_size=params.page_size,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
            status=status,
            delivery_date=delivery_date,
        )
        return PaginatedResponse(
            items=[self._to_summary(row) for row in rows],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=self.proposals.total_pages(total, params.page_size),
        )

    def get_pending_count(self) -> ConsumptionProposalPendingCount:
        return ConsumptionProposalPendingCount(pending_count=self.proposals.count_pending())

    def get(self, proposal_id: uuid.UUID) -> ConsumptionProposalResponse:
        proposal = self.proposals.get_by_id(proposal_id)
        if not proposal:
            raise NotFoundError("Consumption proposal not found")
        return self._to_response(proposal)

    def get_pending_for_delivery_date(
        self,
        delivery_date: date,
    ) -> ConsumptionProposalResponse | None:
        proposal = self.proposals.get_pending_for_delivery_date(delivery_date)
        if not proposal:
            return None
        loaded = self.proposals.get_by_id(proposal.id)
        if not loaded:
            return None
        return self._to_response(loaded)

    def refresh_for_delivery_date(self, delivery_date: date) -> ConsumptionProposalResponse | None:
        orders = self.proposals.get_delivered_unconsumed_orders(delivery_date)
        if not orders:
            pending = self.proposals.get_pending_for_delivery_date(delivery_date)
            if pending:
                self.proposals.delete(pending)
                self.db.commit()
            return None
        return self.generate(
            ConsumptionProposalGenerateRequest(delivery_date=delivery_date),
            user_id=None,
        )

    def generate(
        self,
        payload: ConsumptionProposalGenerateRequest,
        *,
        user_id: uuid.UUID | None,
    ) -> ConsumptionProposalResponse:
        orders = self._resolve_orders(payload)
        if not orders:
            raise ValidationError("No eligible delivered orders found for consumption review")

        delivery_date = payload.delivery_date or orders[0].scheduled_delivery_date
        if any(order.scheduled_delivery_date != delivery_date for order in orders):
            raise ValidationError("All orders must share the same scheduled delivery date")

        blocked = self.proposals.order_ids_in_active_proposals([order.id for order in orders])
        if blocked:
            raise ValidationError(
                "One or more orders are already included in another pending consumption review",
            )

        existing_pending = self.proposals.get_pending_for_delivery_date(delivery_date)
        if existing_pending:
            self.proposals.delete(existing_pending)
            self.db.flush()

        demand_lines = self.demand.build_demand_lines(orders)
        proposal = InventoryConsumptionProposal(
            delivery_date=delivery_date,
            status=ConsumptionProposalStatus.PENDING_REVIEW,
        )
        proposal.proposal_orders = [
            InventoryConsumptionProposalOrder(order_id=order.id) for order in orders
        ]

        proposal_lines: list[InventoryConsumptionProposalLine] = []
        for demand_line in demand_lines:
            effective_qty = demand_line.quantity
            allocation_result = self.fefo.allocate(
                product_item_id=demand_line.product_item_id,
                quantity=effective_qty if demand_line.track_inventory else Decimal("0"),
                unit=demand_line.unit,
            )
            line = InventoryConsumptionProposalLine(
                product_item_id=demand_line.product_item_id,
                demand_type=demand_line.demand_type,
                quantity_proposed=demand_line.quantity,
                quantity_approved=None,
                unit=demand_line.unit,
                quantity_on_hand_snapshot=demand_line.quantity_on_hand,
                track_inventory=demand_line.track_inventory,
                has_shortfall=demand_line.track_inventory and allocation_result.shortfall > 0,
            )
            line.lot_allocations = [
                InventoryConsumptionProposalLotAllocation(
                    lot_id=allocation.lot_id,
                    lot_code=allocation.lot_code,
                    quantity=allocation.quantity,
                    unit=allocation.unit,
                    expires_at=allocation.expires_at,
                )
                for allocation in allocation_result.allocations
            ]
            proposal_lines.append(line)

        proposal.lines = proposal_lines
        self.proposals.create(proposal)
        self.db.commit()

        if user_id:
            self.activity.record(
                action=ActivityAction.CREATED,
                resource_type=ActivityResourceType.CONSUMPTION_PROPOSAL,
                actor_user_id=user_id,
                resource_id=proposal.id,
                resource_label=f"Consumption review {delivery_date.isoformat()}",
                commit=True,
            )

        loaded = self.proposals.get_by_id(proposal.id)
        assert loaded is not None
        return self._to_response(loaded)

    def update(
        self,
        proposal_id: uuid.UUID,
        payload: ConsumptionProposalUpdate,
        *,
        user_id: uuid.UUID,
    ) -> ConsumptionProposalResponse:
        proposal = self.proposals.get_by_id(proposal_id)
        if not proposal:
            raise NotFoundError("Consumption proposal not found")
        if proposal.status != ConsumptionProposalStatus.PENDING_REVIEW:
            raise ValidationError("Only pending proposals can be edited")

        if payload.notes is not None:
            proposal.notes = payload.notes

        if payload.lines is not None:
            line_map = {line.id: line for line in proposal.lines}
            for line_update in payload.lines:
                line = line_map.get(line_update.id)
                if not line:
                    raise NotFoundError("Proposal line not found")
                if line_update.quantity_approved is not None:
                    line.quantity_approved = line_update.quantity_approved.quantize(QTY_PRECISION)
                self._refresh_line_allocations(line)

        self.db.add(proposal)
        self.db.commit()
        self.activity.record(
            action=ActivityAction.UPDATED,
            resource_type=ActivityResourceType.CONSUMPTION_PROPOSAL,
            actor_user_id=user_id,
            resource_id=proposal.id,
            resource_label=f"Updated consumption review {proposal.delivery_date.isoformat()}",
            commit=True,
        )
        loaded = self.proposals.get_by_id(proposal.id)
        assert loaded is not None
        return self._to_response(loaded)

    def approve(self, proposal_id: uuid.UUID, *, user_id: uuid.UUID) -> ConsumptionProposalResponse:
        proposal = self.proposals.get_by_id(proposal_id)
        if not proposal:
            raise NotFoundError("Consumption proposal not found")
        if proposal.status != ConsumptionProposalStatus.PENDING_REVIEW:
            raise ValidationError("Only pending proposals can be approved")

        now = datetime.now(UTC)
        for line in proposal.lines:
            if not line.track_inventory:
                continue
            quantity = self._effective_quantity(line)
            if quantity <= 0:
                continue
            allocation_result = self.fefo.allocate(
                product_item_id=line.product_item_id,
                quantity=quantity,
                unit=line.unit,
            )
            if allocation_result.shortfall > 0:
                item_name = line.product_item.name if line.product_item else str(line.product_item_id)
                raise ValidationError(
                    f"Insufficient stock for {item_name}. Shortfall: "
                    f"{allocation_result.shortfall} {line.unit}",
                )
            for allocation in allocation_result.allocations:
                lot = self.movements.lots.get_by_id(allocation.lot_id)
                if not lot:
                    raise NotFoundError("Inventory lot not found during consumption apply")
                self.movements.record_consumption_movement(
                    lot=lot,
                    quantity=allocation.quantity,
                    reference_id=proposal.id,
                    user_id=user_id,
                    notes=f"Consumption review {proposal.delivery_date.isoformat()}",
                )

        for link in proposal.proposal_orders:
            order = link.order
            order.inventory_consumed_at = now
            order.inventory_consumption_proposal_id = proposal.id
            self.db.add(order)

        proposal.status = ConsumptionProposalStatus.APPROVED
        proposal.reviewed_by_user_id = user_id
        proposal.reviewed_at = now
        proposal.applied_at = now
        self.db.add(proposal)
        self.db.commit()

        self.activity.record(
            action=ActivityAction.UPDATED,
            resource_type=ActivityResourceType.CONSUMPTION_PROPOSAL,
            actor_user_id=user_id,
            resource_id=proposal.id,
            resource_label=f"Approved consumption {proposal.delivery_date.isoformat()}",
            commit=True,
        )
        loaded = self.proposals.get_by_id(proposal.id)
        assert loaded is not None
        return self._to_response(loaded)

    def dismiss(self, proposal_id: uuid.UUID, *, user_id: uuid.UUID) -> ConsumptionProposalResponse:
        proposal = self.proposals.get_by_id(proposal_id)
        if not proposal:
            raise NotFoundError("Consumption proposal not found")
        if proposal.status != ConsumptionProposalStatus.PENDING_REVIEW:
            raise ValidationError("Only pending proposals can be dismissed")

        now = datetime.now(UTC)
        proposal.status = ConsumptionProposalStatus.DISMISSED
        proposal.reviewed_by_user_id = user_id
        proposal.reviewed_at = now
        proposal.proposal_orders.clear()
        self.db.add(proposal)
        self.db.commit()

        self.activity.record(
            action=ActivityAction.UPDATED,
            resource_type=ActivityResourceType.CONSUMPTION_PROPOSAL,
            actor_user_id=user_id,
            resource_id=proposal.id,
            resource_label=f"Dismissed consumption {proposal.delivery_date.isoformat()}",
            commit=True,
        )
        loaded = self.proposals.get_by_id(proposal.id)
        assert loaded is not None
        return self._to_response(loaded)

    def _resolve_orders(self, payload: ConsumptionProposalGenerateRequest) -> list[Order]:
        if payload.order_ids:
            return self.proposals.get_delivered_unconsumed_orders_by_ids(payload.order_ids)
        if payload.delivery_date:
            return self.proposals.get_delivered_unconsumed_orders(payload.delivery_date)
        raise ValidationError("Provide delivery_date or order_ids")

    def _refresh_line_allocations(self, line: InventoryConsumptionProposalLine) -> None:
        line.lot_allocations.clear()
        if not line.track_inventory:
            line.has_shortfall = False
            return
        quantity = self._effective_quantity(line)
        on_hand = self.balances.sum_on_hand(line.product_item_id)
        line.quantity_on_hand_snapshot = on_hand
        allocation_result = self.fefo.allocate(
            product_item_id=line.product_item_id,
            quantity=quantity,
            unit=line.unit,
        )
        line.has_shortfall = allocation_result.shortfall > 0
        line.lot_allocations = [
            InventoryConsumptionProposalLotAllocation(
                lot_id=allocation.lot_id,
                lot_code=allocation.lot_code,
                quantity=allocation.quantity,
                unit=allocation.unit,
                expires_at=allocation.expires_at,
            )
            for allocation in allocation_result.allocations
        ]

    @staticmethod
    def _effective_quantity(line: InventoryConsumptionProposalLine) -> Decimal:
        if line.quantity_approved is not None:
            return line.quantity_approved.quantize(QTY_PRECISION)
        return line.quantity_proposed.quantize(QTY_PRECISION)

    def _to_summary(self, proposal: InventoryConsumptionProposal) -> ConsumptionProposalSummary:
        has_shortfall = any(line.has_shortfall for line in proposal.lines)
        return ConsumptionProposalSummary(
            id=proposal.id,
            delivery_date=proposal.delivery_date,
            status=proposal.status,
            order_count=len(proposal.proposal_orders),
            line_count=len(proposal.lines),
            has_shortfall=has_shortfall,
            created_at=proposal.created_at,
            updated_at=proposal.updated_at,
        )

    def _to_response(self, proposal: InventoryConsumptionProposal) -> ConsumptionProposalResponse:
        lines: list[ConsumptionProposalLineResponse] = []
        for line in proposal.lines:
            effective = self._effective_quantity(line)
            on_hand = line.quantity_on_hand_snapshot
            after = on_hand - effective if line.track_inventory else on_hand
            lines.append(
                ConsumptionProposalLineResponse(
                    id=line.id,
                    product_item_id=line.product_item_id,
                    product_item_name=line.product_item.name if line.product_item else "—",
                    demand_type=line.demand_type,
                    quantity_proposed=line.quantity_proposed,
                    quantity_approved=line.quantity_approved,
                    effective_quantity=effective,
                    unit=line.unit,
                    quantity_on_hand_snapshot=on_hand,
                    quantity_after=after.quantize(QTY_PRECISION),
                    track_inventory=line.track_inventory,
                    has_shortfall=line.has_shortfall,
                    lot_allocations=[
                        ConsumptionProposalLotAllocationResponse.model_validate(row)
                        for row in line.lot_allocations
                    ],
                ),
            )

        orders: list[ConsumptionProposalOrderSummary] = []
        for link in proposal.proposal_orders:
            order = link.order
            customer_name = "—"
            if order.customer:
                customer_name = f"{order.customer.first_name} {order.customer.last_name}".strip()
            orders.append(
                ConsumptionProposalOrderSummary(
                    id=order.id,
                    order_number=order.order_number,
                    customer_name=customer_name,
                    delivered_at=order.delivered_at,
                ),
            )

        return ConsumptionProposalResponse(
            id=proposal.id,
            delivery_date=proposal.delivery_date,
            status=proposal.status,
            notes=proposal.notes,
            reviewed_by_user_id=proposal.reviewed_by_user_id,
            reviewed_at=proposal.reviewed_at,
            applied_at=proposal.applied_at,
            created_at=proposal.created_at,
            updated_at=proposal.updated_at,
            orders=orders,
            lines=lines,
            has_shortfall=any(line.has_shortfall for line in lines),
        )
