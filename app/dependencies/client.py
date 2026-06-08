"""Public client API dependencies."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.customer_catalog_service import CustomerCatalogService
from app.services.customer_checkout_service import CustomerCheckoutService


def get_customer_catalog_service(
    db: Annotated[Session, Depends(get_db)],
) -> CustomerCatalogService:
    return CustomerCatalogService(db)


def get_customer_checkout_service(
    db: Annotated[Session, Depends(get_db)],
) -> CustomerCheckoutService:
    return CustomerCheckoutService(db)
