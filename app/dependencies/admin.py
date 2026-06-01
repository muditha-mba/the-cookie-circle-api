"""Admin-only FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.exceptions import ForbiddenError
from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.collection_service import CollectionService
from app.services.labour_charge_service import LabourChargeService
from app.services.product_item_service import ProductItemService
from app.services.product_item_type_service import ProductItemTypeService
from app.services.product_service import ProductService
from app.services.tax_charge_service import TaxChargeService
from app.services.utility_charge_service import UtilityChargeService


def get_current_admin_user(
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


def get_product_service(
    db: Annotated[Session, Depends(get_db)],
) -> ProductService:
    return ProductService(db)


def get_collection_service(
    db: Annotated[Session, Depends(get_db)],
) -> CollectionService:
    return CollectionService(db)
