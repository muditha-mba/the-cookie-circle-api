"""Production planning routes (read-only operational reporting)."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.dependencies.admin import (
    get_current_admin_user,
    get_production_batch_service,
    get_production_planning_service,
    get_purchase_planning_service,
)
from app.schemas.production_batch import (
    ProductionBatchResponse,
    ProductionBatchUpdate,
)
from app.schemas.purchase_planning import (
    PurchasePlanLine,
    PurchasePlanResponse,
    PurchasePlanStatusUpdate,
)
from app.schemas.production import (
    FulfillmentOverview,
    IngredientRequirementsResponse,
    PackagingRequirementsResponse,
    ProductionBatchesResponse,
    ProductionOrderSummary,
    ProductionSummaryResponse,
    ProductDemandResponse,
)
from app.services.production_batch_service import ProductionBatchService
from app.services.production_planning_service import ProductionPlanningService
from app.services.purchase_planning_service import PurchasePlanningService

router = APIRouter(
    prefix="/production",
    tags=["Production"],
    dependencies=[Depends(get_current_admin_user)],
)


@router.get("/batches", response_model=ProductionBatchesResponse)
def list_production_batches(
    delivery_day_only: Annotated[
        bool,
        Query(description="When true, only dates matching the configured delivery day"),
    ] = False,
    service: Annotated[ProductionPlanningService, Depends(get_production_planning_service)] = ...,
) -> ProductionBatchesResponse:
    """List delivery dates that have scheduled orders."""
    return service.list_batches(delivery_day_only=delivery_day_only)


@router.get("/summary", response_model=ProductionSummaryResponse)
def get_production_summary(
    delivery_date: Annotated[date, Query(description="Scheduled delivery / production date")],
    service: Annotated[ProductionPlanningService, Depends(get_production_planning_service)] = ...,
) -> ProductionSummaryResponse:
    """Full production planning summary for a delivery date."""
    return service.get_summary(delivery_date)


@router.get("/summary/orders", response_model=ProductionOrderSummary)
def get_production_order_summary(
    delivery_date: Annotated[date, Query()],
    service: Annotated[ProductionPlanningService, Depends(get_production_planning_service)] = ...,
) -> ProductionOrderSummary:
    """Order fulfillment summary from financial snapshots."""
    return service.get_order_summary(delivery_date)


@router.get("/product-demand", response_model=ProductDemandResponse)
def get_product_demand(
    delivery_date: Annotated[date, Query()],
    service: Annotated[ProductionPlanningService, Depends(get_production_planning_service)] = ...,
) -> ProductDemandResponse:
    """Aggregated product quantities required for production."""
    return service.get_product_demand(delivery_date)


@router.get("/ingredients", response_model=IngredientRequirementsResponse)
def get_ingredient_requirements(
    delivery_date: Annotated[date, Query()],
    service: Annotated[ProductionPlanningService, Depends(get_production_planning_service)] = ...,
) -> IngredientRequirementsResponse:
    """Ingredient requirements from current product recipes."""
    return service.get_ingredient_requirements(delivery_date)


@router.get("/packaging", response_model=PackagingRequirementsResponse)
def get_packaging_requirements(
    delivery_date: Annotated[date, Query()],
    service: Annotated[ProductionPlanningService, Depends(get_production_planning_service)] = ...,
) -> PackagingRequirementsResponse:
    """Packaging requirements from current collection configurations."""
    return service.get_packaging_requirements(delivery_date)


@router.get("/fulfillment", response_model=FulfillmentOverview)
def get_fulfillment_overview(
    delivery_date: Annotated[date, Query()],
    service: Annotated[ProductionPlanningService, Depends(get_production_planning_service)] = ...,
) -> FulfillmentOverview:
    """Orders for a delivery date grouped by fulfillment status."""
    return service.get_fulfillment_overview(delivery_date)


@router.get("/planning-batch", response_model=ProductionBatchResponse)
def get_planning_batch(
    delivery_date: Annotated[date, Query()],
    auto_create: Annotated[bool, Query()] = True,
    service: Annotated[ProductionBatchService, Depends(get_production_batch_service)] = ...,
) -> ProductionBatchResponse:
    """Get or create the production planning batch for a delivery date."""
    return service.get_or_create_for_date(delivery_date, auto_create=auto_create)


@router.patch("/planning-batch/{batch_id}", response_model=ProductionBatchResponse)
def update_planning_batch(
    batch_id: uuid.UUID,
    payload: ProductionBatchUpdate,
    service: Annotated[ProductionBatchService, Depends(get_production_batch_service)] = ...,
) -> ProductionBatchResponse:
    """Update production batch status or notes."""
    return service.update(batch_id, payload)


@router.get("/purchase-plan", response_model=PurchasePlanResponse)
def get_purchase_plan(
    delivery_date: Annotated[date, Query()],
    service: Annotated[PurchasePlanningService, Depends(get_purchase_planning_service)] = ...,
) -> PurchasePlanResponse:
    """Purchase planning list for a production date."""
    return service.get_purchase_plan(delivery_date)


@router.patch("/purchase-plan/status", response_model=PurchasePlanLine)
def update_purchase_plan_status(
    payload: PurchasePlanStatusUpdate,
    service: Annotated[PurchasePlanningService, Depends(get_purchase_planning_service)] = ...,
) -> PurchasePlanLine:
    """Update purchase planning status for an item."""
    return service.update_purchase_status(payload)


@router.get("/purchase-plan/export")
def export_purchase_plan(
    delivery_date: Annotated[date, Query()],
    service: Annotated[PurchasePlanningService, Depends(get_purchase_planning_service)] = ...,
) -> Response:
    """Download purchase list CSV grouped by supplier."""
    filename, content = service.export_csv(delivery_date)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export")
def export_production_summary(
    delivery_date: Annotated[date, Query()],
    service: Annotated[ProductionPlanningService, Depends(get_production_planning_service)] = ...,
) -> Response:
    """Download production summary as CSV."""
    filename, content = service.export_csv(delivery_date)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
