"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings
from app.middleware.admin_audit import setup_admin_audit
from app.middleware.cors import setup_cors
from app.middleware.rate_limit import setup_rate_limit
from app.middleware.security_headers import setup_security_headers
from app.routers.activity_logs import router as activity_logs_router
from app.routers.analytics import router as analytics_router
from app.routers.auth import router as auth_router
from app.routers.business_settings import router as business_settings_router
from app.routers.client_account import router as client_account_router
from app.routers.client_ordering import router as client_ordering_router
from app.routers.client_site import router as client_site_router
from app.routers.faq_categories import router as faq_categories_router
from app.routers.faqs import router as faqs_router
from app.routers.reviews import router as reviews_router
from app.routers.shared_memories import router as shared_memories_router
from app.routers.collections import router as collections_router
from app.routers.collection_packages import router as collection_packages_router
from app.routers.customers import router as customers_router
from app.routers.dashboard import router as dashboard_router
from app.routers.delivery_areas import router as delivery_areas_router
from app.routers.orders import router as orders_router
from app.routers.production import router as production_router
from app.routers.purchase_receipts import router as purchase_receipts_router
from app.routers.suppliers import router as suppliers_router
from app.routers.health import router as health_router
from app.routers.inventory import router as inventory_router
from app.routers.labour_charges import router as labour_charges_router
from app.routers.media import router as media_router
from app.routers.product_item_types import router as product_item_types_router
from app.routers.product_categories import router as product_categories_router
from app.routers.product_items import router as product_items_router
from app.routers.products import router as products_router
from app.routers.tax_charges import router as tax_charges_router
from app.routers.users import router as users_router
from app.routers.utility_charges import router as utility_charges_router
from app.routers.discount_rules import router as discount_rules_router
from app.routers.discounts import router as discounts_router
from app.routers.promotion_slides import router as promotion_slides_router
from app.routers.tools import router as tools_router
from app.routers.client_promotions import router as client_promotions_router
from app.routers.payments import router as payments_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Application startup and shutdown lifecycle."""
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    docs_kwargs = {}
    if settings.is_production:
        docs_kwargs = {
            "docs_url": None,
            "redoc_url": None,
            "openapi_url": None,
        }

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
        **docs_kwargs,
    )

    if settings.is_staging or settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.trusted_host_list,
        )

    setup_security_headers(app)
    setup_admin_audit(app)
    setup_rate_limit(app)
    setup_cors(app)

    app.include_router(health_router)
    app.include_router(media_router, prefix=settings.api_v1_prefix)
    app.include_router(auth_router, prefix=settings.api_v1_prefix)
    app.include_router(client_ordering_router, prefix=settings.api_v1_prefix)
    app.include_router(client_site_router, prefix=settings.api_v1_prefix)
    app.include_router(client_account_router, prefix=settings.api_v1_prefix)
    app.include_router(faqs_router, prefix=settings.api_v1_prefix)
    app.include_router(faq_categories_router, prefix=settings.api_v1_prefix)
    app.include_router(shared_memories_router, prefix=settings.api_v1_prefix)
    app.include_router(reviews_router, prefix=settings.api_v1_prefix)
    app.include_router(product_item_types_router, prefix=settings.api_v1_prefix)
    app.include_router(product_items_router, prefix=settings.api_v1_prefix)
    app.include_router(utility_charges_router, prefix=settings.api_v1_prefix)
    app.include_router(labour_charges_router, prefix=settings.api_v1_prefix)
    app.include_router(tax_charges_router, prefix=settings.api_v1_prefix)
    app.include_router(products_router, prefix=settings.api_v1_prefix)
    app.include_router(product_categories_router, prefix=settings.api_v1_prefix)
    app.include_router(collections_router, prefix=settings.api_v1_prefix)
    app.include_router(collection_packages_router, prefix=settings.api_v1_prefix)
    app.include_router(business_settings_router, prefix=settings.api_v1_prefix)
    app.include_router(customers_router, prefix=settings.api_v1_prefix)
    app.include_router(dashboard_router, prefix=settings.api_v1_prefix)
    app.include_router(delivery_areas_router, prefix=settings.api_v1_prefix)
    app.include_router(orders_router, prefix=settings.api_v1_prefix)
    app.include_router(production_router, prefix=settings.api_v1_prefix)
    app.include_router(suppliers_router, prefix=settings.api_v1_prefix)
    app.include_router(inventory_router, prefix=settings.api_v1_prefix)
    app.include_router(purchase_receipts_router, prefix=settings.api_v1_prefix)
    app.include_router(analytics_router, prefix=settings.api_v1_prefix)
    app.include_router(activity_logs_router, prefix=settings.api_v1_prefix)
    app.include_router(users_router, prefix=settings.api_v1_prefix)
    app.include_router(discount_rules_router, prefix=settings.api_v1_prefix)
    app.include_router(discounts_router, prefix=settings.api_v1_prefix)
    app.include_router(promotion_slides_router, prefix=settings.api_v1_prefix)
    app.include_router(client_promotions_router, prefix=settings.api_v1_prefix)
    app.include_router(payments_router, prefix=settings.api_v1_prefix)
    app.include_router(tools_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
