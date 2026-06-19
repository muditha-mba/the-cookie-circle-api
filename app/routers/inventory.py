"""Inventory routes."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.enums import ConsumptionProposalStatus, InventoryMovementType
from app.dependencies.admin import (
    get_consumption_proposal_service,
    get_current_admin_user,
    get_inventory_balance_service,
    get_inventory_expense_service,
    get_inventory_lot_service,
    get_inventory_movement_service,
)
from app.dependencies.permissions import require_super_admin
from app.models.user import User
from app.schemas.consumption_proposal import (
    ConsumptionProposalGenerateRequest,
    ConsumptionProposalPendingCount,
    ConsumptionProposalResponse,
    ConsumptionProposalSummary,
    ConsumptionProposalUpdate,
)
from app.schemas.inventory import (
    InventoryAdjustmentCreate,
    InventoryAlertResponse,
    InventoryBalanceDetailResponse,
    InventoryBalanceResponse,
    InventoryLotSummary,
    InventoryMovementResponse,
    InventoryWasteCreate,
)
from app.schemas.inventory_readiness import InventoryExpenseSummaryResponse
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.services.consumption_proposal_service import ConsumptionProposalService
from app.services.inventory_balance_service import InventoryBalanceService
from app.services.inventory_expense_service import InventoryExpenseService
from app.services.inventory_lot_service import InventoryLotService
from app.services.inventory_movement_service import InventoryMovementService

router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"],
    dependencies=[Depends(require_super_admin)],
)


@router.get("/balances", response_model=PaginatedResponse[InventoryBalanceResponse])
def list_inventory_balances(
    params: Annotated[PaginationParams, Depends()],
    low_stock_only: Annotated[bool, Query()] = False,
    service: Annotated[InventoryBalanceService, Depends(get_inventory_balance_service)] = ...,
) -> PaginatedResponse[InventoryBalanceResponse]:
    """List on-hand balances for tracked product items."""
    return service.list_balances(params, low_stock_only=low_stock_only)


@router.get("/balances/{product_item_id}", response_model=InventoryBalanceDetailResponse)
def get_inventory_balance(
    product_item_id: uuid.UUID,
    service: Annotated[InventoryBalanceService, Depends(get_inventory_balance_service)] = ...,
) -> InventoryBalanceDetailResponse:
    """Balance detail with active lots for a tracked product item."""
    return service.get_balance(product_item_id)


@router.get("/alerts", response_model=InventoryAlertResponse)
def get_inventory_alerts(
    expiring_within_days: Annotated[int, Query(ge=1, le=90)] = 7,
    service: Annotated[InventoryBalanceService, Depends(get_inventory_balance_service)] = ...,
) -> InventoryAlertResponse:
    """Low-stock, expiry, consumption, and upcoming shortfall alert counts."""
    return service.get_alerts(expiring_within_days=expiring_within_days)


@router.get("/expense-summary", response_model=InventoryExpenseSummaryResponse)
def get_inventory_expense_summary(
    from_date: Annotated[date, Query()],
    to_date: Annotated[date, Query()],
    service: Annotated[InventoryExpenseService, Depends(get_inventory_expense_service)] = ...,
) -> InventoryExpenseSummaryResponse:
    """Confirmed purchase receipt spend for a date range."""
    return service.get_summary(from_date=from_date, to_date=to_date)


@router.get("/lots", response_model=PaginatedResponse[InventoryLotSummary])
def list_inventory_lots(
    params: Annotated[PaginationParams, Depends()],
    product_item_id: Annotated[uuid.UUID | None, Query()] = None,
    expiring_before: Annotated[date | None, Query()] = None,
    service: Annotated[InventoryLotService, Depends(get_inventory_lot_service)] = ...,
) -> PaginatedResponse[InventoryLotSummary]:
    """List inventory lots."""
    return service.list(
        params,
        product_item_id=product_item_id,
        expiring_before=expiring_before,
    )


@router.get("/lots/{lot_id}", response_model=InventoryLotSummary)
def get_inventory_lot(
    lot_id: uuid.UUID,
    service: Annotated[InventoryLotService, Depends(get_inventory_lot_service)] = ...,
) -> InventoryLotSummary:
    """Get a single inventory lot."""
    return service.get(lot_id)


@router.get("/movements", response_model=PaginatedResponse[InventoryMovementResponse])
def list_inventory_movements(
    params: Annotated[PaginationParams, Depends()],
    product_item_id: Annotated[uuid.UUID | None, Query()] = None,
    lot_id: Annotated[uuid.UUID | None, Query()] = None,
    movement_type: Annotated[InventoryMovementType | None, Query()] = None,
    service: Annotated[InventoryMovementService, Depends(get_inventory_movement_service)] = ...,
) -> PaginatedResponse[InventoryMovementResponse]:
    """Inventory movement audit trail."""
    return service.list_movements(
        params,
        product_item_id=product_item_id,
        lot_id=lot_id,
        movement_type=movement_type,
    )


@router.post("/adjustments", response_model=InventoryMovementResponse, status_code=status.HTTP_201_CREATED)
def create_inventory_adjustment(
    payload: InventoryAdjustmentCreate,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    service: Annotated[InventoryMovementService, Depends(get_inventory_movement_service)] = ...,
) -> InventoryMovementResponse:
    """Manual stock adjustment on a lot."""
    return service.adjust(payload, user_id=current_user.id)


@router.post("/waste", response_model=InventoryMovementResponse, status_code=status.HTTP_201_CREATED)
def record_inventory_waste(
    payload: InventoryWasteCreate,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    service: Annotated[InventoryMovementService, Depends(get_inventory_movement_service)] = ...,
) -> InventoryMovementResponse:
    """Record waste on a lot."""
    return service.record_waste(payload, user_id=current_user.id)


@router.get("/consumption-proposals/pending-count", response_model=ConsumptionProposalPendingCount)
def get_consumption_pending_count(
    service: Annotated[ConsumptionProposalService, Depends(get_consumption_proposal_service)] = ...,
) -> ConsumptionProposalPendingCount:
    """Count of consumption proposals awaiting review."""
    return service.get_pending_count()


@router.get("/consumption-proposals", response_model=PaginatedResponse[ConsumptionProposalSummary])
def list_consumption_proposals(
    params: Annotated[PaginationParams, Depends()],
    proposal_status: Annotated[ConsumptionProposalStatus | None, Query(alias="status")] = None,
    delivery_date: Annotated[date | None, Query()] = None,
    service: Annotated[ConsumptionProposalService, Depends(get_consumption_proposal_service)] = ...,
) -> PaginatedResponse[ConsumptionProposalSummary]:
    """List consumption proposals."""
    return service.list(params, status=proposal_status, delivery_date=delivery_date)


@router.post(
    "/consumption-proposals/generate",
    response_model=ConsumptionProposalResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_consumption_proposal(
    payload: ConsumptionProposalGenerateRequest,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    service: Annotated[ConsumptionProposalService, Depends(get_consumption_proposal_service)] = ...,
) -> ConsumptionProposalResponse:
    """Manually generate or refresh a consumption review."""
    return service.generate(payload, user_id=current_user.id)


@router.get("/consumption-proposals/by-date/{delivery_date}", response_model=ConsumptionProposalResponse | None)
def get_pending_consumption_for_date(
    delivery_date: date,
    service: Annotated[ConsumptionProposalService, Depends(get_consumption_proposal_service)] = ...,
) -> ConsumptionProposalResponse | None:
    """Pending consumption proposal for a delivery date, if any."""
    return service.get_pending_for_delivery_date(delivery_date)


@router.get("/consumption-proposals/{proposal_id}", response_model=ConsumptionProposalResponse)
def get_consumption_proposal(
    proposal_id: uuid.UUID,
    service: Annotated[ConsumptionProposalService, Depends(get_consumption_proposal_service)] = ...,
) -> ConsumptionProposalResponse:
    """Consumption proposal detail."""
    return service.get(proposal_id)


@router.patch("/consumption-proposals/{proposal_id}", response_model=ConsumptionProposalResponse)
def update_consumption_proposal(
    proposal_id: uuid.UUID,
    payload: ConsumptionProposalUpdate,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    service: Annotated[ConsumptionProposalService, Depends(get_consumption_proposal_service)] = ...,
) -> ConsumptionProposalResponse:
    """Update approved quantities or notes on a pending proposal."""
    return service.update(proposal_id, payload, user_id=current_user.id)


@router.post("/consumption-proposals/{proposal_id}/approve", response_model=ConsumptionProposalResponse)
def approve_consumption_proposal(
    proposal_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    service: Annotated[ConsumptionProposalService, Depends(get_consumption_proposal_service)] = ...,
) -> ConsumptionProposalResponse:
    """Approve proposal and deduct stock."""
    return service.approve(proposal_id, user_id=current_user.id)


@router.post("/consumption-proposals/{proposal_id}/dismiss", response_model=ConsumptionProposalResponse)
def dismiss_consumption_proposal(
    proposal_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    service: Annotated[ConsumptionProposalService, Depends(get_consumption_proposal_service)] = ...,
) -> ConsumptionProposalResponse:
    """Dismiss a pending proposal without changing stock."""
    return service.dismiss(proposal_id, user_id=current_user.id)
