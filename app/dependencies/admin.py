"""Admin-only FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.exceptions import ForbiddenError
from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.security import enforce_admin_ip_allowlist
from app.models.user import User
from app.services.business_setting_service import BusinessSettingService
from app.services.collection_service import CollectionService
from app.services.collection_package_service import CollectionPackageService
from app.services.analytics.analytics_collection_service import AnalyticsCollectionService
from app.services.analytics.analytics_customer_service import AnalyticsCustomerService
from app.services.analytics.analytics_executive_service import AnalyticsExecutiveService
from app.services.analytics.analytics_export_service import AnalyticsExportService
from app.services.analytics.analytics_kpi_service import AnalyticsKpiService
from app.services.analytics.analytics_operations_service import AnalyticsOperationsService
from app.services.analytics.analytics_order_service import AnalyticsOrderService
from app.services.analytics.analytics_overview_service import AnalyticsOverviewService
from app.services.analytics.analytics_product_service import AnalyticsProductService
from app.services.analytics.analytics_production_service import AnalyticsProductionService
from app.services.analytics.analytics_production_ux_service import AnalyticsProductionUxService
from app.services.analytics.analytics_revenue_service import AnalyticsRevenueService
from app.services.overhead_analytics_service import OverheadAnalyticsService
from app.services.customer_communication_service import CustomerCommunicationService
from app.services.customer_insights_service import CustomerInsightsService
from app.services.customer_note_service import CustomerNoteService
from app.services.customer_service import CustomerService
from app.services.delivery_area_service import DeliveryAreaService
from app.services.faq_category_service import FaqCategoryService
from app.services.faq_service import FaqService
from app.services.consumption_proposal_service import ConsumptionProposalService
from app.services.inventory_balance_service import InventoryBalanceService
from app.services.inventory_lot_service import InventoryLotService
from app.services.inventory_movement_service import InventoryMovementService
from app.services.purchase_receipt_service import PurchaseReceiptService
from app.services.shared_memory_service import SharedMemoryService
from app.services.dashboard_service import DashboardService
from app.services.order_service import OrderService
from app.services.production_batch_service import ProductionBatchService
from app.services.production_planning_service import ProductionPlanningService
from app.services.purchase_planning_service import PurchasePlanningService
from app.services.supplier_service import SupplierService
from app.services.user_lookup_service import UserLookupService
from app.services.labour_charge_service import LabourChargeService
from app.services.product_item_service import ProductItemService
from app.services.product_item_type_service import ProductItemTypeService
from app.services.product_service import ProductService
from app.services.tax_charge_service import TaxChargeService
from app.services.activity_log_service import ActivityLogService
from app.services.utility_charge_service import UtilityChargeService
from app.services.customer_discount_grant_service import CustomerDiscountGrantService
from app.services.customer_discount_override_service import CustomerDiscountOverrideService
from app.services.discount_audit_service import DiscountAuditService
from app.services.discount_rule_service import DiscountRuleService
from app.services.promotion_slide_service import PromotionSlideService
from app.services.recipe_calculator_service import RecipeCalculatorService


def get_current_admin_user(
    _: Annotated[None, Depends(enforce_admin_ip_allowlist)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Require an authenticated admin user."""
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenError("Admin access required")
    return current_user


def get_product_item_type_service(
    db: Annotated[Session, Depends(get_db)],
) -> ProductItemTypeService:
    return ProductItemTypeService(db)


def get_product_item_service(
    db: Annotated[Session, Depends(get_db)],
) -> ProductItemService:
    return ProductItemService(db)


def get_utility_charge_service(
    db: Annotated[Session, Depends(get_db)],
) -> UtilityChargeService:
    return UtilityChargeService(db)


def get_labour_charge_service(
    db: Annotated[Session, Depends(get_db)],
) -> LabourChargeService:
    return LabourChargeService(db)


def get_tax_charge_service(
    db: Annotated[Session, Depends(get_db)],
) -> TaxChargeService:
    return TaxChargeService(db)


def get_discount_rule_service(
    db: Annotated[Session, Depends(get_db)],
) -> DiscountRuleService:
    return DiscountRuleService(db)


def get_customer_discount_grant_service(
    db: Annotated[Session, Depends(get_db)],
) -> CustomerDiscountGrantService:
    return CustomerDiscountGrantService(db)


def get_customer_discount_override_service(
    db: Annotated[Session, Depends(get_db)],
) -> CustomerDiscountOverrideService:
    return CustomerDiscountOverrideService(db)


def get_discount_audit_service(
    db: Annotated[Session, Depends(get_db)],
) -> DiscountAuditService:
    return DiscountAuditService(db)


def get_promotion_slide_service(
    db: Annotated[Session, Depends(get_db)],
) -> PromotionSlideService:
    return PromotionSlideService(db)


def get_product_service(
    db: Annotated[Session, Depends(get_db)],
) -> ProductService:
    return ProductService(db)


def get_collection_service(
    db: Annotated[Session, Depends(get_db)],
) -> CollectionService:
    return CollectionService(db)


def get_collection_package_service(
    db: Annotated[Session, Depends(get_db)],
) -> CollectionPackageService:
    return CollectionPackageService(db)


def get_business_setting_service(
    db: Annotated[Session, Depends(get_db)],
) -> BusinessSettingService:
    return BusinessSettingService(db)


def get_customer_service(
    db: Annotated[Session, Depends(get_db)],
) -> CustomerService:
    return CustomerService(db)


def get_customer_insights_service(
    db: Annotated[Session, Depends(get_db)],
) -> CustomerInsightsService:
    return CustomerInsightsService(db)


def get_customer_note_service(
    db: Annotated[Session, Depends(get_db)],
) -> CustomerNoteService:
    return CustomerNoteService(db)


def get_customer_communication_service(
    db: Annotated[Session, Depends(get_db)],
) -> CustomerCommunicationService:
    return CustomerCommunicationService(db)


def get_order_service(
    db: Annotated[Session, Depends(get_db)],
) -> OrderService:
    return OrderService(db)


def get_dashboard_service(
    db: Annotated[Session, Depends(get_db)],
) -> DashboardService:
    return DashboardService(db)


def get_delivery_area_service(
    db: Annotated[Session, Depends(get_db)],
) -> DeliveryAreaService:
    return DeliveryAreaService(db)


def get_user_lookup_service(
    db: Annotated[Session, Depends(get_db)],
) -> UserLookupService:
    return UserLookupService(db)


def get_production_planning_service(
    db: Annotated[Session, Depends(get_db)],
) -> ProductionPlanningService:
    return ProductionPlanningService(db)


def get_supplier_service(
    db: Annotated[Session, Depends(get_db)],
) -> SupplierService:
    return SupplierService(db)


def get_production_batch_service(
    db: Annotated[Session, Depends(get_db)],
) -> ProductionBatchService:
    return ProductionBatchService(db)


def get_purchase_planning_service(
    db: Annotated[Session, Depends(get_db)],
) -> PurchasePlanningService:
    return PurchasePlanningService(db)


def get_analytics_overview_service(
    db: Annotated[Session, Depends(get_db)],
) -> AnalyticsOverviewService:
    return AnalyticsOverviewService(db)


def get_analytics_kpi_service(
    db: Annotated[Session, Depends(get_db)],
) -> AnalyticsKpiService:
    return AnalyticsKpiService(db)


def get_analytics_revenue_service(
    db: Annotated[Session, Depends(get_db)],
) -> AnalyticsRevenueService:
    return AnalyticsRevenueService(db)


def get_analytics_order_service(
    db: Annotated[Session, Depends(get_db)],
) -> AnalyticsOrderService:
    return AnalyticsOrderService(db)


def get_analytics_product_service(
    db: Annotated[Session, Depends(get_db)],
) -> AnalyticsProductService:
    return AnalyticsProductService(db)


def get_analytics_collection_service(
    db: Annotated[Session, Depends(get_db)],
) -> AnalyticsCollectionService:
    return AnalyticsCollectionService(db)


def get_analytics_customer_service(
    db: Annotated[Session, Depends(get_db)],
) -> AnalyticsCustomerService:
    return AnalyticsCustomerService(db)


def get_analytics_production_service(
    db: Annotated[Session, Depends(get_db)],
) -> AnalyticsProductionService:
    return AnalyticsProductionService(db)


def get_analytics_production_ux_service(
    db: Annotated[Session, Depends(get_db)],
) -> AnalyticsProductionUxService:
    return AnalyticsProductionUxService(db)


def get_analytics_operations_service(
    db: Annotated[Session, Depends(get_db)],
) -> AnalyticsOperationsService:
    return AnalyticsOperationsService(db)


def get_analytics_executive_service(
    db: Annotated[Session, Depends(get_db)],
) -> AnalyticsExecutiveService:
    return AnalyticsExecutiveService(db)


def get_analytics_export_service(
    db: Annotated[Session, Depends(get_db)],
) -> AnalyticsExportService:
    return AnalyticsExportService(db)


def get_overhead_analytics_service(
    db: Annotated[Session, Depends(get_db)],
) -> OverheadAnalyticsService:
    return OverheadAnalyticsService(db)


def get_faq_service(
    db: Annotated[Session, Depends(get_db)],
) -> FaqService:
    return FaqService(db)


def get_faq_category_service(
    db: Annotated[Session, Depends(get_db)],
) -> FaqCategoryService:
    return FaqCategoryService(db)


def get_shared_memory_service(
    db: Annotated[Session, Depends(get_db)],
) -> SharedMemoryService:
    return SharedMemoryService(db)


def get_activity_log_service(
    db: Annotated[Session, Depends(get_db)],
) -> ActivityLogService:
    return ActivityLogService(db)


def get_inventory_balance_service(
    db: Annotated[Session, Depends(get_db)],
) -> InventoryBalanceService:
    return InventoryBalanceService(db)


def get_inventory_lot_service(
    db: Annotated[Session, Depends(get_db)],
) -> InventoryLotService:
    return InventoryLotService(db)


def get_inventory_movement_service(
    db: Annotated[Session, Depends(get_db)],
) -> InventoryMovementService:
    return InventoryMovementService(db)


def get_purchase_receipt_service(
    db: Annotated[Session, Depends(get_db)],
) -> PurchaseReceiptService:
    return PurchaseReceiptService(db)


def get_consumption_proposal_service(
    db: Annotated[Session, Depends(get_db)],
) -> ConsumptionProposalService:
    return ConsumptionProposalService(db)


def get_inventory_readiness_service(
    db: Annotated[Session, Depends(get_db)],
):
    from app.services.inventory_readiness_service import InventoryReadinessService

    return InventoryReadinessService(db)


def get_inventory_expense_service(
    db: Annotated[Session, Depends(get_db)],
):
    from app.services.inventory_expense_service import InventoryExpenseService

    return InventoryExpenseService(db)


def get_recipe_calculator_service(
    db: Annotated[Session, Depends(get_db)],
) -> RecipeCalculatorService:
    return RecipeCalculatorService(db)
