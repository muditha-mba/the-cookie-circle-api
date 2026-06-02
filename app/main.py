"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.core.config import settings
from app.middleware.cors import setup_cors
from app.routers.analytics import router as analytics_router
from app.routers.auth import router as auth_router
from app.routers.business_settings import router as business_settings_router
from app.routers.collections import router as collections_router
from app.routers.collection_packages import router as collection_packages_router
from app.routers.customers import router as customers_router
from app.routers.dashboard import router as dashboard_router
from app.routers.delivery_areas import router as delivery_areas_router
from app.routers.orders import router as orders_router
from app.routers.production import router as production_router
from app.routers.suppliers import router as suppliers_router
from app.routers.health import router as health_router
from app.routers.labour_charges import router as labour_charges_router
from app.routers.product_item_types import router as product_item_types_router
from app.routers.product_items import router as product_items_router
from app.routers.products import router as products_router
from app.routers.tax_charges import router as tax_charges_router
from app.routers.users import router as users_router
from app.routers.utility_charges import router as utility_charges_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Application startup and shutdown lifecycle."""
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )

    setup_cors(app)
    app.include_router(health_router)
    app.include_router(auth_router, prefix=settings.api_v1_prefix)
    app.include_router(product_item_types_router, prefix=settings.api_v1_prefix)
    app.include_router(product_items_router, prefix=settings.api_v1_prefix)
    app.include_router(utility_charges_router, prefix=settings.api_v1_prefix)
    app.include_router(labour_charges_router, prefix=settings.api_v1_prefix)
    app.include_router(tax_charges_router, prefix=settings.api_v1_prefix)
    app.include_router(products_router, prefix=settings.api_v1_prefix)
    app.include_router(collections_router, prefix=settings.api_v1_prefix)
    app.include_router(collection_packages_router, prefix=settings.api_v1_prefix)
    app.include_router(business_settings_router, prefix=settings.api_v1_prefix)
    app.include_router(customers_router, prefix=settings.api_v1_prefix)
    app.include_router(dashboard_router, prefix=settings.api_v1_prefix)
    app.include_router(delivery_areas_router, prefix=settings.api_v1_prefix)
    app.include_router(orders_router, prefix=settings.api_v1_prefix)
    app.include_router(production_router, prefix=settings.api_v1_prefix)
    app.include_router(suppliers_router, prefix=settings.api_v1_prefix)
    app.include_router(analytics_router, prefix=settings.api_v1_prefix)
    app.include_router(users_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
