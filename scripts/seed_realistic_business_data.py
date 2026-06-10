"""Seed realistic Cookie Circle business data for operations/analytics validation.

This script intentionally creates production-like data (not synthetic placeholders)
covering products, collections, customers, orders, production batches, and
purchase planning before Inventory Foundation work.
"""

from __future__ import annotations

import argparse
import random
import sys
import traceback
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, inspect, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401  # Ensure all SQLAlchemy models are registered.
from app.core.enums import (
    CustomerSource,
    MarketingSource,
    OrderSource,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    ProductionBatchStatus,
    PurchasePlanningStatus,
    UserRole,
    Weekday,
)
from app.core.security import hash_password
from app.database.base import Base
from app.database.session import SessionLocal, engine
from app.models.business_setting import BusinessSetting
from app.models.collection_package import CollectionPackage
from app.models.order import Order
from app.models.order_status_event import OrderStatusEvent
from app.models.product_item_type import ProductItemType
from app.models.user import User
from app.schemas.business_settings import BusinessSettingsUpdate
from app.schemas.collection import CollectionCreate, CollectionItemLineInput
from app.schemas.client_ordering import CollectionCookieSelectionInput
from app.schemas.collection_package import CollectionPackageCreate
from app.schemas.customer import CustomerCreate
from app.schemas.delivery_area import DeliveryAreaCreate
from app.schemas.order import OrderCollectionLineInput, OrderCreate, OrderProductLineInput, OrderUpdate
from app.schemas.product import ProductCreate, RecipeLineInput
from app.schemas.product_item import ProductItemCreate
from app.schemas.product_item_type import ProductItemTypeCreate
from app.schemas.production_batch import ProductionBatchUpdate
from app.schemas.purchase_planning import PurchasePlanStatusUpdate
from app.schemas.supplier import SupplierCreate
from app.services.business_setting_service import BusinessSettingService
from app.services.collection_service import CollectionService
from app.services.collection_package_service import CollectionPackageService
from app.services.customer_service import CustomerService
from app.services.delivery_area_service import DeliveryAreaService
from app.services.order_service import OrderService
from app.services.product_item_service import ProductItemService
from app.services.product_item_type_service import ProductItemTypeService
from app.services.product_service import ProductService
from app.services.production_batch_service import ProductionBatchService
from app.services.purchase_planning_service import PurchasePlanningService
from app.services.supplier_service import SupplierService
from app.utils.email import normalize_email

MONEY = Decimal("0.01")
QTY = Decimal("0.0001")
RNG_SEED = 20260602


CATEGORY_BY_PRODUCT: dict[str, str] = {
    "Classic Chocolate Chip Cookie": "CHOCOLATE",
    "White Chocolate Chip Cookie": "CHOCOLATE",
    "Double Chocolate Chip Cookie": "CHOCOLATE",
    "Double Chocolate White Chip Cookie": "CHOCOLATE",
    "Unicorn Cookie": "KIDS_FAVOURITES",
    "Smarties Cookie": "KIDS_FAVOURITES",
    "White & Dark Chocolate Chip Cookie": "KIDS_FAVOURITES",
    "Sugar Free Chocolate Chip Cookie": "HEALTHY",
    "Sugar Free Date Cookie": "HEALTHY",
    "Fruit & Nut Chocolate Chip Cookie": "NUTTY",
    "Mixed Nut Chocolate Chip Cookie": "NUTTY",
    "Cashew Chocolate Chip Cookie": "NUTTY",
    "Classic Butter Cookie": "BUTTER",
    "Cashew Butter Cookie": "BUTTER",
}

PACKAGE_ALLOWED_CATEGORIES: dict[str, tuple[str, ...]] = {
    "SPECIAL_EDITION": ("CHOCOLATE", "KIDS_FAVOURITES", "HEALTHY", "NUTTY"),
    "MIX_AND_MATCH": ("CHOCOLATE", "KIDS_FAVOURITES", "HEALTHY", "NUTTY"),
    "BUTTER_COLLECTION": ("BUTTER",),
}

PACKAGE_FEES: dict[str, Decimal] = {
    "SPECIAL_EDITION": Decimal("350"),
    "MIX_AND_MATCH": Decimal("0"),
    "BUTTER_COLLECTION": Decimal("0"),
}

PACKAGE_SIZES: dict[str, int] = {
    "The Signature Circle": 6,
    "The Golden Circle": 10,
    "The Grand Circle": 14,
    "The Little Circle": 4,
    "The Family Circle": 8,
    "The Party Circle": 12,
    "The Tea Circle": 8,
    "The Warm Circle": 14,
    "The Gathering Circle": 20,
}


@dataclass(frozen=True)
class ProductSpec:
    name: str
    unit_price: Decimal
    yield_quantity: Decimal
    buffer_amount: Decimal
    recipe: list[tuple[str, Decimal]]
    is_premium: bool = False


@dataclass(frozen=True)
class CollectionSpec:
    name: str
    description: str
    package_code: str


PRODUCT_SPECS: tuple[ProductSpec, ...] = (
    ProductSpec(
        name="Classic Chocolate Chip Cookie",
        unit_price=Decimal("295"),
        yield_quantity=Decimal("18"),
        buffer_amount=Decimal("200"),
        recipe=[
            ("Astra Margarine", Decimal("250")),
            ("White Sugar", Decimal("220")),
            ("Brown Sugar", Decimal("240")),
            ("Eggs", Decimal("2")),
            ("Flour", Decimal("350")),
            ("Chocolate Chips", Decimal("250")),
            ("Vanilla", Decimal("10")),
            ("Baking Soda", Decimal("5")),
            ("Oil Paper", Decimal("1")),
        ],
    ),
    ProductSpec(
        name="White Chocolate Chip Cookie",
        unit_price=Decimal("295"),
        yield_quantity=Decimal("18"),
        buffer_amount=Decimal("200"),
        recipe=[
            ("Astra Margarine", Decimal("250")),
            ("White Sugar", Decimal("220")),
            ("Brown Sugar", Decimal("240")),
            ("Eggs", Decimal("2")),
            ("Flour", Decimal("350")),
            ("White Chocolate Chips", Decimal("250")),
            ("Vanilla", Decimal("10")),
            ("Baking Soda", Decimal("5")),
            ("Oil Paper", Decimal("1")),
        ],
    ),
    ProductSpec(
        name="Double Chocolate Chip Cookie",
        unit_price=Decimal("340"),
        yield_quantity=Decimal("18"),
        buffer_amount=Decimal("200"),
        recipe=[
            ("Astra Margarine", Decimal("250")),
            ("White Sugar", Decimal("220")),
            ("Brown Sugar", Decimal("240")),
            ("Eggs", Decimal("2")),
            ("Flour", Decimal("350")),
            ("Chocolate Chips", Decimal("250")),
            ("Cacao Powder", Decimal("100")),
            ("Vanilla", Decimal("10")),
            ("Baking Soda", Decimal("5")),
            ("Oil Paper", Decimal("1")),
        ],
        is_premium=True,
    ),
    ProductSpec(
        name="Double Chocolate White Chip Cookie",
        unit_price=Decimal("340"),
        yield_quantity=Decimal("18"),
        buffer_amount=Decimal("200"),
        recipe=[
            ("Astra Margarine", Decimal("250")),
            ("White Sugar", Decimal("220")),
            ("Brown Sugar", Decimal("240")),
            ("Eggs", Decimal("2")),
            ("Flour", Decimal("350")),
            ("White Chocolate Chips", Decimal("250")),
            ("Cacao Powder", Decimal("100")),
            ("Vanilla", Decimal("10")),
            ("Baking Soda", Decimal("5")),
            ("Oil Paper", Decimal("1")),
        ],
        is_premium=True,
    ),
    ProductSpec(
        name="Unicorn Cookie",
        unit_price=Decimal("300"),
        yield_quantity=Decimal("18"),
        buffer_amount=Decimal("200"),
        recipe=[
            ("Astra Margarine", Decimal("250")),
            ("White Sugar", Decimal("220")),
            ("Brown Sugar", Decimal("240")),
            ("Eggs", Decimal("2")),
            ("Flour", Decimal("350")),
            ("Color Vermicelli", Decimal("200")),
            ("Vanilla", Decimal("10")),
            ("Baking Soda", Decimal("5")),
            ("Oil Paper", Decimal("1")),
        ],
    ),
    ProductSpec(
        name="Smarties Cookie",
        unit_price=Decimal("295"),
        yield_quantity=Decimal("18"),
        buffer_amount=Decimal("200"),
        recipe=[
            ("Astra Margarine", Decimal("250")),
            ("White Sugar", Decimal("220")),
            ("Brown Sugar", Decimal("240")),
            ("Eggs", Decimal("2")),
            ("Flour", Decimal("350")),
            ("Smarties", Decimal("250")),
            ("Vanilla", Decimal("10")),
            ("Baking Soda", Decimal("5")),
            ("Oil Paper", Decimal("1")),
        ],
    ),
    ProductSpec(
        name="White & Dark Chocolate Chip Cookie",
        unit_price=Decimal("295"),
        yield_quantity=Decimal("18"),
        buffer_amount=Decimal("200"),
        recipe=[
            ("Astra Margarine", Decimal("250")),
            ("White Sugar", Decimal("220")),
            ("Brown Sugar", Decimal("240")),
            ("Eggs", Decimal("2")),
            ("Flour", Decimal("350")),
            ("Chocolate Chips", Decimal("125")),
            ("White Chocolate Chips", Decimal("125")),
            ("Vanilla", Decimal("10")),
            ("Baking Soda", Decimal("5")),
            ("Oil Paper", Decimal("1")),
        ],
    ),
    ProductSpec(
        name="Sugar Free Chocolate Chip Cookie",
        unit_price=Decimal("300"),
        yield_quantity=Decimal("8"),
        buffer_amount=Decimal("200"),
        recipe=[
            ("Bananas", Decimal("2")),
            ("Oats", Decimal("120")),
            ("Chocolate Chips", Decimal("40")),
            ("Cashew", Decimal("40")),
        ],
    ),
    ProductSpec(
        name="Sugar Free Date Cookie",
        unit_price=Decimal("300"),
        yield_quantity=Decimal("8"),
        buffer_amount=Decimal("200"),
        recipe=[
            ("Bananas", Decimal("2")),
            ("Oats", Decimal("120")),
            ("Dates", Decimal("40")),
            ("Cashew", Decimal("40")),
        ],
    ),
    ProductSpec(
        name="Fruit & Nut Chocolate Chip Cookie",
        unit_price=Decimal("360"),
        yield_quantity=Decimal("18"),
        buffer_amount=Decimal("200"),
        recipe=[
            ("Astra Margarine", Decimal("250")),
            ("White Sugar", Decimal("220")),
            ("Brown Sugar", Decimal("240")),
            ("Eggs", Decimal("2")),
            ("Flour", Decimal("350")),
            ("Chocolate Chips", Decimal("125")),
            ("Fruit & Nut", Decimal("125")),
            ("Vanilla", Decimal("10")),
            ("Baking Soda", Decimal("5")),
            ("Oil Paper", Decimal("1")),
        ],
        is_premium=True,
    ),
    ProductSpec(
        name="Mixed Nut Chocolate Chip Cookie",
        unit_price=Decimal("360"),
        yield_quantity=Decimal("18"),
        buffer_amount=Decimal("200"),
        recipe=[
            ("Astra Margarine", Decimal("250")),
            ("White Sugar", Decimal("220")),
            ("Brown Sugar", Decimal("240")),
            ("Eggs", Decimal("2")),
            ("Flour", Decimal("350")),
            ("Chocolate Chips", Decimal("125")),
            ("Mixed Nut", Decimal("125")),
            ("Vanilla", Decimal("10")),
            ("Baking Soda", Decimal("5")),
            ("Oil Paper", Decimal("1")),
        ],
        is_premium=True,
    ),
    ProductSpec(
        name="Cashew Chocolate Chip Cookie",
        unit_price=Decimal("360"),
        yield_quantity=Decimal("18"),
        buffer_amount=Decimal("200"),
        recipe=[
            ("Astra Margarine", Decimal("250")),
            ("White Sugar", Decimal("220")),
            ("Brown Sugar", Decimal("240")),
            ("Eggs", Decimal("2")),
            ("Flour", Decimal("350")),
            ("Chocolate Chips", Decimal("125")),
            ("Cashew", Decimal("125")),
            ("Vanilla", Decimal("10")),
            ("Baking Soda", Decimal("5")),
            ("Oil Paper", Decimal("1")),
        ],
        is_premium=True,
    ),
    ProductSpec(
        name="Classic Butter Cookie",
        unit_price=Decimal("90"),
        yield_quantity=Decimal("25"),
        buffer_amount=Decimal("200"),
        recipe=[
            ("Sugar", Decimal("60")),
            ("Flour", Decimal("250")),
            ("Butter", Decimal("250")),
            ("Vanilla", Decimal("5")),
            ("Oil Paper", Decimal("1")),
        ],
    ),
    ProductSpec(
        name="Cashew Butter Cookie",
        unit_price=Decimal("120"),
        yield_quantity=Decimal("25"),
        buffer_amount=Decimal("200"),
        recipe=[
            ("Sugar", Decimal("60")),
            ("Flour", Decimal("250")),
            ("Butter", Decimal("250")),
            ("Cashew", Decimal("100")),
            ("Vanilla", Decimal("5")),
            ("Oil Paper", Decimal("1")),
        ],
        is_premium=True,
    ),
)

COLLECTION_SPECS: tuple[CollectionSpec, ...] = (
    CollectionSpec(
        name="The Signature Circle",
        description="Special Edition Collection — pack of 6; premium and classic cookie mix.",
        package_code="SPECIAL_EDITION",
    ),
    CollectionSpec(
        name="The Golden Circle",
        description="Special Edition — build your own 10-cookie gift pack.",
        package_code="SPECIAL_EDITION",
    ),
    CollectionSpec(
        name="The Grand Circle",
        description="Special Edition — build your own 14-cookie celebration pack.",
        package_code="SPECIAL_EDITION",
    ),
    CollectionSpec(
        name="The Little Circle",
        description="Mix & Match — build your own 4-cookie pack.",
        package_code="MIX_AND_MATCH",
    ),
    CollectionSpec(
        name="The Family Circle",
        description="Mix & Match — build your own 8-cookie pack.",
        package_code="MIX_AND_MATCH",
    ),
    CollectionSpec(
        name="The Party Circle",
        description="Mix & Match — build your own 12-cookie pack.",
        package_code="MIX_AND_MATCH",
    ),
    CollectionSpec(
        name="The Tea Circle",
        description="Butter Collection — build your own 8-cookie butter assortment.",
        package_code="BUTTER_COLLECTION",
    ),
    CollectionSpec(
        name="The Warm Circle",
        description="Butter Collection — build your own 14-cookie butter assortment.",
        package_code="BUTTER_COLLECTION",
    ),
    CollectionSpec(
        name="The Gathering Circle",
        description="Butter Collection — build your own 20-cookie butter assortment.",
        package_code="BUTTER_COLLECTION",
    ),
)

SUPPLIER_PAYLOADS: tuple[dict[str, str], ...] = (
    {
        "supplier_name": "Lanka Baking Supplies",
        "contact_person": "Nuwan Perera",
        "email": "orders@lankabakingsupplies.lk",
        "phone": "+94771234567",
        "notes": "Core baking ingredients and weekly replenishment.",
    },
    {
        "supplier_name": "Sweet Ingredients Lanka",
        "contact_person": "Sashini Fernando",
        "email": "sales@sweetingredients.lk",
        "phone": "+94772223344",
        "notes": "Sugar variants, vanilla, and specialty sweeteners.",
    },
    {
        "supplier_name": "Premium Nut Suppliers",
        "contact_person": "Ravindu Senanayake",
        "email": "trade@premiumnuts.lk",
        "phone": "+94773334455",
        "notes": "Cashew, mixed nut, and fruit-nut blends.",
    },
    {
        "supplier_name": "Chocolate World Lanka",
        "contact_person": "Tharindu Rajapaksha",
        "email": "b2b@chocolateworld.lk",
        "phone": "+94774445566",
        "notes": "Dark and white chocolate chips, cacao powder, Smarties.",
    },
    {
        "supplier_name": "Packaging House LK",
        "contact_person": "Madhavi Silva",
        "email": "accounts@packaginghouselk.lk",
        "phone": "+94775556677",
        "notes": "Cookie boxes and packaging consumables.",
    },
    {
        "supplier_name": "Fresh Dairy Suppliers",
        "contact_person": "Kavindu Wijesinghe",
        "email": "hello@freshdairy.lk",
        "phone": "+94776667788",
        "notes": "Butter, margarine, eggs, and chilled inputs.",
    },
)

PRODUCT_ITEM_PAYLOADS: tuple[dict[str, Any], ...] = (
    {"name": "Astra Margarine", "type": "Ingredient", "price": "550", "qty": "250", "unit": "grams", "supplier": "Fresh Dairy Suppliers"},
    {"name": "White Sugar", "type": "Ingredient", "price": "60", "qty": "220", "unit": "grams", "supplier": "Sweet Ingredients Lanka"},
    {"name": "Brown Sugar", "type": "Ingredient", "price": "70", "qty": "240", "unit": "grams", "supplier": "Sweet Ingredients Lanka"},
    {"name": "Sugar", "type": "Ingredient", "price": "17", "qty": "60", "unit": "grams", "supplier": "Sweet Ingredients Lanka"},
    {"name": "Eggs", "type": "Ingredient", "price": "120", "qty": "2", "unit": "units", "supplier": "Fresh Dairy Suppliers"},
    {"name": "Flour", "type": "Ingredient", "price": "140", "qty": "350", "unit": "grams", "supplier": "Lanka Baking Supplies"},
    {"name": "Chocolate Chips", "type": "Ingredient", "price": "800", "qty": "250", "unit": "grams", "supplier": "Chocolate World Lanka"},
    {"name": "White Chocolate Chips", "type": "Ingredient", "price": "800", "qty": "250", "unit": "grams", "supplier": "Chocolate World Lanka"},
    {"name": "Cacao Powder", "type": "Ingredient", "price": "1050", "qty": "100", "unit": "grams", "supplier": "Chocolate World Lanka"},
    {"name": "Vanilla", "type": "Ingredient", "price": "80", "qty": "10", "unit": "ml", "supplier": "Sweet Ingredients Lanka"},
    {"name": "Baking Soda", "type": "Ingredient", "price": "9.5", "qty": "5", "unit": "grams", "supplier": "Lanka Baking Supplies"},
    {"name": "Color Vermicelli", "type": "Ingredient", "price": "800", "qty": "200", "unit": "grams", "supplier": "Chocolate World Lanka"},
    {"name": "Smarties", "type": "Ingredient", "price": "556", "qty": "250", "unit": "grams", "supplier": "Chocolate World Lanka"},
    {"name": "Bananas", "type": "Ingredient", "price": "200", "qty": "2", "unit": "units", "supplier": "Lanka Baking Supplies"},
    {"name": "Oats", "type": "Ingredient", "price": "216", "qty": "120", "unit": "grams", "supplier": "Lanka Baking Supplies"},
    {"name": "Dates", "type": "Ingredient", "price": "84", "qty": "40", "unit": "grams", "supplier": "Sweet Ingredients Lanka"},
    {"name": "Cashew", "type": "Ingredient", "price": "575", "qty": "125", "unit": "grams", "supplier": "Premium Nut Suppliers"},
    {"name": "Fruit & Nut", "type": "Ingredient", "price": "700", "qty": "125", "unit": "grams", "supplier": "Premium Nut Suppliers"},
    {"name": "Mixed Nut", "type": "Ingredient", "price": "700", "qty": "125", "unit": "grams", "supplier": "Premium Nut Suppliers"},
    {"name": "Butter", "type": "Ingredient", "price": "575", "qty": "250", "unit": "grams", "supplier": "Fresh Dairy Suppliers"},
    {"name": "Oil Paper", "type": "Packaging", "price": "14", "qty": "1", "unit": "sheet", "supplier": "Packaging House LK"},
    {"name": "Cookie Box", "type": "Packaging", "price": "120", "qty": "1", "unit": "box", "supplier": "Packaging House LK"},
)

DELIVERY_AREAS: tuple[dict[str, Any], ...] = (
    {"name": "Kandy", "delivery_fee_override": Decimal("700"), "pickup_only": False},
    {"name": "Asgiriya", "delivery_fee_override": Decimal("700"), "pickup_only": False},
    {"name": "Mulgampola", "delivery_fee_override": Decimal("700"), "pickup_only": False},
    {"name": "Bowalawatta", "delivery_fee_override": Decimal("700"), "pickup_only": False},
    {"name": "Peradeniya", "delivery_fee_override": Decimal("500"), "pickup_only": False},
    {"name": "Aniwatta", "delivery_fee_override": Decimal("500"), "pickup_only": False},
    {"name": "Kiribathkumbura", "delivery_fee_override": Decimal("500"), "pickup_only": False},
    {"name": "Pilimathalawa", "delivery_fee_override": Decimal("500"), "pickup_only": False},
    {"name": "Kadugannawa", "delivery_fee_override": Decimal("500"), "pickup_only": False},
    {"name": "Gelioya", "delivery_fee_override": Decimal("500"), "pickup_only": False},
    {"name": "Katugastota", "delivery_fee_override": Decimal("650"), "pickup_only": False},
    {"name": "Watapuluwa", "delivery_fee_override": Decimal("650"), "pickup_only": False},
    {"name": "Ampitiya", "delivery_fee_override": Decimal("750"), "pickup_only": False},
    {"name": "Tennekumbura", "delivery_fee_override": Decimal("750"), "pickup_only": False},
    {"name": "Kundasale", "delivery_fee_override": Decimal("750"), "pickup_only": False},
    {"name": "Akurana", "delivery_fee_override": Decimal("650"), "pickup_only": False},
    {"name": "Danture", "delivery_fee_override": Decimal("650"), "pickup_only": False},
    {"name": "Poththapitiya", "delivery_fee_override": Decimal("650"), "pickup_only": False},
    {"name": "Gampola", "delivery_fee_override": Decimal("800"), "pickup_only": False},
    {"name": "Pickup Only", "delivery_fee_override": Decimal("0"), "pickup_only": True},
)

FIRST_NAMES = [
    "Kasun", "Nimali", "Tharindu", "Sachini", "Dilan", "Ayesha", "Ravindu", "Dinuli", "Nuwan", "Shanika",
    "Kavindu", "Madhavi", "Janith", "Upeksha", "Thisara", "Piumi", "Chamath", "Nethmi", "Amila", "Ishara",
    "Roshan", "Dilani", "Harsha", "Sewmini", "Lahiru", "Sanduni", "Gayan", "Vihangi", "Bimal", "Akila",
]
LAST_NAMES = [
    "Perera", "Fernando", "Silva", "Senanayake", "Jayasinghe", "Gunawardena", "Rathnayake", "Wijesinghe",
    "Bandara", "Karunaratne", "Ekanayake", "Dissanayake", "Abeysekera", "Rajapaksha", "Weerasinghe", "Hettiarachchi",
    "Kumara", "Mendis", "Nawarathna", "Samarasinghe",
]
CITIES = ["Kandy", "Peradeniya", "Katugastota", "Kundasale", "Akurana", "Gampola", "Pilimathalawa"]
MARKETING_POOL = [
    MarketingSource.INSTAGRAM,
    MarketingSource.FACEBOOK,
    MarketingSource.WHATSAPP,
    MarketingSource.TIKTOK,
    MarketingSource.LINKEDIN,
    MarketingSource.YOUTUBE,
    MarketingSource.TWITTER,
    MarketingSource.PINTEREST,
    MarketingSource.EMAIL,
    MarketingSource.GOOGLE,
    MarketingSource.REFERRAL,
    MarketingSource.WALK_IN,
]


def first_day_of_month(d: date) -> date:
    return d.replace(day=1)


def month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        nxt = date(year + 1, 1, 1)
    else:
        nxt = date(year, month + 1, 1)
    end = nxt - timedelta(days=1)
    return start, end


def saturdays_in_month(year: int, month: int) -> list[date]:
    start, end = month_bounds(year, month)
    days: list[date] = []
    cursor = start
    while cursor <= end:
        if cursor.weekday() == 5:
            days.append(cursor)
        cursor += timedelta(days=1)
    return days


def random_saturday_in_month(rng: random.Random, year: int, month: int) -> date:
    sats = saturdays_in_month(year, month)
    if not sats:
        start, _ = month_bounds(year, month)
        return start
    return rng.choice(sats)


def weighted_choice(rng: random.Random, weights: list[tuple[Any, int]]) -> Any:
    values = [item for item, _ in weights]
    probs = [w for _, w in weights]
    return rng.choices(values, weights=probs, k=1)[0]


def clear_business_data(db: Session) -> dict[str, int]:
    keep_tables = {
        "users",
        "refresh_tokens",
        "password_reset_tokens",
        "email_verification_tokens",
        "roles",
        "permissions",
        "role_permissions",
        "user_roles",
        "alembic_version",
    }

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    deleted_counts: dict[str, int] = {}

    # Delete in reverse dependency order to satisfy foreign keys.
    for table in reversed(Base.metadata.sorted_tables):
        table_name = table.name
        if table_name not in existing_tables:
            continue
        if table_name in keep_tables:
            continue
        result = db.execute(delete(table))
        deleted_counts[table_name] = int(result.rowcount or 0)

    db.commit()
    return dict(sorted(deleted_counts.items()))


def ensure_product_item_types(db: Session) -> dict[str, ProductItemType]:
    service = ProductItemTypeService(db)
    existing = {
        row.name.lower(): row
        for row in db.scalars(select(ProductItemType)).all()
    }

    out: dict[str, ProductItemType] = {}
    for name, description in (
        ("Ingredient", "Raw ingredients used in cookie recipes."),
        ("Packaging", "Packaging and consumables used for cookie delivery."),
    ):
        current = existing.get(name.lower())
        if current is None:
            created = service.create(
                ProductItemTypeCreate(name=name, description=description, is_active=True),
            )
            current = db.get(ProductItemType, created.id)
        assert current is not None
        out[name] = current
    return out


def seed_suppliers(db: Session) -> dict[str, uuid.UUID]:
    import uuid

    service = SupplierService(db)
    ids: dict[str, uuid.UUID] = {}
    for payload in SUPPLIER_PAYLOADS:
        created = service.create(SupplierCreate(**payload, is_active=True))
        ids[created.supplier_name] = created.id
    return ids


def seed_product_items(
    db: Session,
    item_types: dict[str, ProductItemType],
    supplier_ids: dict[str, Any],
) -> dict[str, Any]:
    service = ProductItemService(db)
    ids: dict[str, Any] = {}
    for row in PRODUCT_ITEM_PAYLOADS:
        created = service.create(
            ProductItemCreate(
                item_type_id=item_types[row["type"]].id,
                name=row["name"],
                description=None,
                purchase_price=Decimal(str(row["price"])).quantize(MONEY),
                purchase_quantity=Decimal(str(row["qty"])).quantize(QTY),
                purchase_unit=row["unit"],
                primary_supplier_id=supplier_ids[row["supplier"]],
                is_active=True,
            ),
        )
        ids[created.name] = created.id
    return ids


CATEGORY_DEFAULTS: tuple[dict[str, Any], ...] = (
    {
        "id": "a1000001-0000-4000-8000-000000000001",
        "code": "CHOCOLATE",
        "name": "Chocolate",
        "sort_order": 1,
    },
    {
        "id": "a1000001-0000-4000-8000-000000000002",
        "code": "KIDS_FAVOURITES",
        "name": "Kids Favourites",
        "sort_order": 2,
    },
    {
        "id": "a1000001-0000-4000-8000-000000000003",
        "code": "HEALTHY",
        "name": "Healthy",
        "sort_order": 3,
    },
    {
        "id": "a1000001-0000-4000-8000-000000000004",
        "code": "NUTTY",
        "name": "Nutty",
        "sort_order": 4,
    },
    {
        "id": "a1000001-0000-4000-8000-000000000005",
        "code": "BUTTER",
        "name": "Butter",
        "sort_order": 5,
    },
)


def ensure_product_categories(db: Session) -> dict[str, Any]:
    """Recreate canonical categories after clear_business_data wipes them."""
    from app.models.product_category import ProductCategory

    ids: dict[str, Any] = {}
    for row in CATEGORY_DEFAULTS:
        existing = db.scalar(select(ProductCategory).where(ProductCategory.code == row["code"]))
        if existing is None:
            category = ProductCategory(
                id=row["id"],
                code=row["code"],
                name=row["name"],
                sort_order=row["sort_order"],
                is_active=True,
            )
            db.add(category)
            db.flush()
            ids[row["code"]] = category.id
        else:
            ids[existing.code] = existing.id
    db.commit()
    return ids


def load_category_ids(db: Session) -> dict[str, Any]:
    from app.models.product_category import ProductCategory

    rows = db.scalars(select(ProductCategory)).all()
    return {row.code: row.id for row in rows}


def seed_products(
    db: Session,
    product_item_ids: dict[str, Any],
    category_ids: dict[str, Any],
) -> dict[str, Any]:
    service = ProductService(db)
    ids: dict[str, Any] = {}
    for spec in PRODUCT_SPECS:
        batch_selling_price = (spec.unit_price * spec.yield_quantity).quantize(MONEY)
        category_code = CATEGORY_BY_PRODUCT[spec.name]
        payload = ProductCreate(
            name=spec.name,
            description=(
                "Premium cookie" if spec.is_premium else "Signature cookie"
            ) + " seeded for realistic six-month operations analytics.",
            category_id=category_ids[category_code],
            selling_price=batch_selling_price,
            buffer_amount=spec.buffer_amount,
            yield_quantity=spec.yield_quantity,
            production_notes=(
                "Premium recipe with higher-value ingredients."
                if spec.is_premium
                else "Core production recipe."
            ),
            is_active=True,
            is_public=True,
            recipe_lines=[
                RecipeLineInput(product_item_id=product_item_ids[item_name], quantity=qty)
                for item_name, qty in spec.recipe
            ],
            utility_charge_ids=[],
            labour_charge_ids=[],
            tax_charge_ids=[],
        )
        created = service.create(payload)
        ids[created.name] = created.id
    return ids


def seed_collections(
    db: Session,
    category_ids: dict[str, Any],
    cookie_box_id: Any,
) -> dict[str, Any]:
    service = CollectionService(db)
    package_ids = {
        row.code: row.id
        for row in db.scalars(select(CollectionPackage)).all()
    }
    ids: dict[str, Any] = {}
    for spec in COLLECTION_SPECS:
        allowed_codes = PACKAGE_ALLOWED_CATEGORIES[spec.package_code]
        payload = CollectionCreate(
            name=spec.name,
            description=spec.description,
            package_id=package_ids[spec.package_code],
            package_size=PACKAGE_SIZES[spec.name],
            package_fee=PACKAGE_FEES[spec.package_code],
            is_active=True,
            is_public=True,
            allowed_category_ids=[category_ids[code] for code in allowed_codes],
            item_lines=[CollectionItemLineInput(product_item_id=cookie_box_id, quantity=Decimal("1"))],
            utility_charge_ids=[],
            labour_charge_ids=[],
            tax_charge_ids=[],
        )
        created = service.create(payload)
        ids[created.name] = created.id
    return ids


def ensure_collection_packages(db: Session) -> dict[str, Any]:
    service = CollectionPackageService(db)
    defaults = (
        {
            "code": "SPECIAL_EDITION",
            "name": "Special Edition",
            "description": "Premium and curated gift collections.",
            "badge_tone": "violet",
        },
        {
            "code": "MIX_AND_MATCH",
            "name": "Mix & Match",
            "description": "Flexible mixed bundles with premium limits.",
            "badge_tone": "blue",
        },
        {
            "code": "BUTTER_COLLECTION",
            "name": "Butter Collection",
            "description": "Tea-time butter cookie focused bundles.",
            "badge_tone": "amber",
        },
    )
    ids: dict[str, Any] = {}
    for row in defaults:
        existing = db.scalar(select(CollectionPackage).where(CollectionPackage.code == row["code"]))
        if existing is None:
            created = service.create(
                CollectionPackageCreate(
                    code=row["code"],
                    name=row["name"],
                    description=row["description"],
                    badge_tone=row["badge_tone"],
                    is_active=True,
                ),
            )
            ids[created.code] = created.id
        else:
            ids[existing.code] = existing.id
    return ids


def seed_delivery_areas(db: Session) -> dict[str, Any]:
    service = DeliveryAreaService(db)
    ids: dict[str, Any] = {}
    for row in DELIVERY_AREAS:
        created = service.create(
            DeliveryAreaCreate(
                name=row["name"],
                description=f"Operational delivery zone: {row['name']}",
                delivery_fee_override=row["delivery_fee_override"],
                pickup_only=row["pickup_only"],
                is_active=True,
            ),
        )
        ids[created.name] = created.id
    return ids


def seed_customers(db: Session, rng: random.Random, count: int = 50) -> list[Any]:
    service = CustomerService(db)
    customers: list[Any] = []
    existing_user_emails = set(db.scalars(select(User.email)).all())

    registered_count = 18
    guest_count = 17
    manual_count = count - registered_count - guest_count

    # Create customer auth users only for registered profiles.
    for idx in range(registered_count):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        email_base = normalize_email(f"{first.lower()}.{last.lower()}.{idx+1}@cookiecircle.lk")
        email = email_base
        suffix = 1
        while email in existing_user_emails:
            suffix += 1
            email = normalize_email(
                f"{first.lower()}.{last.lower()}.{idx+1}.{suffix}@cookiecircle.lk",
            )
        existing_user_emails.add(email)
        user = User(
            email=email,
            password_hash=hash_password("CookieCircle123!"),
            role=UserRole.CUSTOMER,
            first_name=first,
            last_name=last,
            email_verified=True,
            is_active=True,
        )
        db.add(user)
        db.flush()

        created = service.create(
            CustomerCreate(
                user_id=user.id,
                first_name=first,
                last_name=last,
                email=email,
                phone=f"+9477{rng.randint(1000000, 9999999)}",
                address_line_1=f"No. {rng.randint(1, 250)}",
                address_line_2="",
                city=rng.choice(CITIES),
                postal_code=str(rng.randint(20000, 20999)),
                landmark="Near town center",
                source=CustomerSource.REGISTERED,
                marketing_source=rng.choice(MARKETING_POOL),
                notes="Registered customer seeded for realistic analytics.",
                is_active=True,
            ),
        )
        customers.append(created)

    for _ in range(guest_count):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        created = service.create(
            CustomerCreate(
                user_id=None,
                first_name=first,
                last_name=last,
                email=f"{first.lower()}.{last.lower()}@example.com",
                phone=f"+9476{rng.randint(1000000, 9999999)}",
                address_line_1=f"No. {rng.randint(1, 250)}",
                address_line_2="",
                city=rng.choice(CITIES),
                postal_code=str(rng.randint(20000, 20999)),
                landmark="Guest checkout",
                source=CustomerSource.GUEST,
                marketing_source=rng.choice(MARKETING_POOL),
                notes="Guest customer seeded for order diversity.",
                is_active=True,
            ),
        )
        customers.append(created)

    for _ in range(manual_count):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        created = service.create(
            CustomerCreate(
                user_id=None,
                first_name=first,
                last_name=last,
                email=None,
                phone=f"+9471{rng.randint(1000000, 9999999)}",
                address_line_1=f"No. {rng.randint(1, 250)}",
                address_line_2="",
                city=rng.choice(CITIES),
                postal_code=str(rng.randint(20000, 20999)),
                landmark="Manual / phone order",
                source=CustomerSource.MANUAL,
                marketing_source=rng.choice(MARKETING_POOL),
                notes="Manual customer seeded from offline channels.",
                is_active=True,
            ),
        )
        customers.append(created)

    return customers


def build_random_selections(
    rng: random.Random,
    collection_name: str,
    product_ids: dict[str, Any],
) -> list[CollectionCookieSelectionInput]:
    package_size = PACKAGE_SIZES[collection_name]
    package_code = next(
        spec.package_code for spec in COLLECTION_SPECS if spec.name == collection_name
    )
    allowed_codes = set(PACKAGE_ALLOWED_CATEGORIES[package_code])
    eligible = [
        name
        for name, code in CATEGORY_BY_PRODUCT.items()
        if code in allowed_codes and name in product_ids
    ]
    if not eligible:
        raise RuntimeError(f"No eligible products for collection {collection_name}")

    remaining = package_size
    selections: list[CollectionCookieSelectionInput] = []
    while remaining > 0:
        product_name = rng.choice(eligible)
        qty = rng.randint(1, remaining)
        remaining -= qty
        product_id = product_ids[product_name]
        existing = next((row for row in selections if row.product_id == product_id), None)
        if existing is None:
            selections.append(
                CollectionCookieSelectionInput(product_id=product_id, quantity=Decimal(str(qty))),
            )
        else:
            selections = [
                CollectionCookieSelectionInput(
                    product_id=row.product_id,
                    quantity=row.quantity + Decimal(str(qty)),
                )
                if row.product_id == product_id
                else row
                for row in selections
            ]
    return selections


def choose_lines_for_order(
    rng: random.Random,
    product_ids: dict[str, Any],
    collection_ids: dict[str, Any],
) -> tuple[list[OrderProductLineInput], list[OrderCollectionLineInput]]:
    popular_collections = [
        "The Tea Circle",
        "The Little Circle",
        "The Family Circle",
    ]
    popular_products = [
        "Classic Chocolate Chip Cookie",
        "Classic Butter Cookie",
    ]

    is_collection_order = rng.random() < 0.60
    if is_collection_order:
        collection_name = weighted_choice(
            rng,
            [
                (popular_collections[0], 28),
                (popular_collections[1], 24),
                (popular_collections[2], 24),
                ("The Signature Circle", 8),
                ("The Golden Circle", 5),
                ("The Grand Circle", 3),
                ("The Party Circle", 4),
                ("The Warm Circle", 2),
                ("The Gathering Circle", 2),
            ],
        )
        quantity = Decimal("1") if rng.random() < 0.82 else Decimal("2")
        selections = build_random_selections(rng, collection_name, product_ids)
        return [], [
            OrderCollectionLineInput(
                collection_id=collection_ids[collection_name],
                quantity=quantity,
                selections=selections,
            ),
        ]

    # Product order
    product_name = weighted_choice(
        rng,
        [
            (popular_products[0], 26),
            (popular_products[1], 24),
            ("White Chocolate Chip Cookie", 9),
            ("Unicorn Cookie", 8),
            ("Smarties Cookie", 8),
            ("Sugar Free Date Cookie", 6),
            ("Sugar Free Chocolate Chip Cookie", 6),
            ("Double Chocolate Chip Cookie", 4),
            ("Double Chocolate White Chip Cookie", 3),
            ("Fruit & Nut Chocolate Chip Cookie", 2),
            ("Mixed Nut Chocolate Chip Cookie", 2),
            ("Cashew Chocolate Chip Cookie", 2),
            ("Cashew Butter Cookie", 2),
            ("White & Dark Chocolate Chip Cookie", 4),
        ],
    )
    quantity = Decimal(str(rng.choice([4, 6, 8, 10, 12, 15, 18, 20])))
    return [OrderProductLineInput(product_id=product_ids[product_name], quantity=quantity)], []


def assign_status_and_payment(rng: random.Random, scheduled_date: date) -> tuple[OrderStatus, PaymentStatus, PaymentMethod]:
    status = weighted_choice(
        rng,
        [
            (OrderStatus.DELIVERED, 80),
            (OrderStatus.CONFIRMED, 10),
            (OrderStatus.PREPARING, 5),
            (OrderStatus.READY, 3),
            (OrderStatus.CANCELLED, 2),
        ],
    )

    if scheduled_date >= date.today() and status == OrderStatus.DELIVERED:
        status = OrderStatus.CONFIRMED

    method = weighted_choice(
        rng,
        [
            (PaymentMethod.CASH_ON_DELIVERY, 46),
            (PaymentMethod.BANK_TRANSFER, 28),
            (PaymentMethod.MANUAL, 20),
            (PaymentMethod.STRIPE, 6),
        ],
    )

    if status == OrderStatus.DELIVERED:
        payment = weighted_choice(
            rng,
            [
                (PaymentStatus.PAID, 94),
                (PaymentStatus.PENDING, 4),
                (PaymentStatus.FAILED, 1),
                (PaymentStatus.REFUNDED, 1),
            ],
        )
    elif status == OrderStatus.CANCELLED:
        payment = weighted_choice(
            rng,
            [
                (PaymentStatus.PENDING, 60),
                (PaymentStatus.REFUNDED, 30),
                (PaymentStatus.PAID, 10),
            ],
        )
    else:
        payment = weighted_choice(
            rng,
            [
                (PaymentStatus.PENDING, 70),
                (PaymentStatus.PAID, 25),
                (PaymentStatus.FAILED, 5),
            ],
        )

    return status, payment, method


def create_orders(
    db: Session,
    rng: random.Random,
    customers: list[Any],
    product_ids: dict[str, Any],
    collection_ids: dict[str, Any],
    delivery_area_ids: dict[str, Any],
) -> tuple[int, int, dict[str, int]]:
    order_service = OrderService(db)

    # Increasing monthly order counts across the last 6 completed months.
    today = date.today()
    month_anchor = first_day_of_month(today)
    monthly_counts = [14, 18, 22, 26, 30, 34]

    past_order_ids: list[Any] = []
    future_order_ids: list[Any] = []
    status_counter: dict[str, int] = defaultdict(int)

    repeat_pool = customers[:20]

    for month_offset, count in enumerate(monthly_counts, start=6):
        ref = month_anchor - timedelta(days=30 * month_offset)
        year, month = ref.year, ref.month

        for _ in range(count):
            customer = rng.choice(repeat_pool if rng.random() < 0.60 else customers)
            requested = random_saturday_in_month(rng, year, month)
            scheduled = requested

            product_lines, collection_lines = choose_lines_for_order(
                rng,
                product_ids,
                collection_ids,
            )

            source = weighted_choice(
                rng,
                [
                    (OrderSource.WHATSAPP, 36),
                    (OrderSource.INSTAGRAM, 20),
                    (OrderSource.FACEBOOK, 16),
                    (OrderSource.WEBSITE, 14),
                    (OrderSource.WALK_IN, 8),
                    (OrderSource.PHONE, 4),
                    (OrderSource.MANUAL, 2),
                ],
            )
            status, payment_status, payment_method = assign_status_and_payment(rng, scheduled)

            area_name = weighted_choice(
                rng,
                [
                    ("Peradeniya", 22),
                    ("Kandy", 20),
                    ("Katugastota", 14),
                    ("Kundasale", 12),
                    ("Akurana", 12),
                    ("Gampola", 10),
                    ("Pickup Only", 10),
                ],
            )

            created = order_service.create(
                OrderCreate(
                    customer_id=customer.id,
                    delivery_area_id=delivery_area_ids[area_name],
                    source=source,
                    payment_method=payment_method,
                    payment_status=payment_status,
                    status=OrderStatus.PENDING,
                    customer_notes="Seeded realistic order.",
                    internal_notes="Generated by realistic business seeder.",
                    requested_delivery_date=requested,
                    product_lines=product_lines,
                    collection_lines=collection_lines,
                    delivery_contact_name=f"{customer.first_name} {customer.last_name}",
                    delivery_phone_primary=customer.phone,
                    delivery_phone_secondary=None,
                    delivery_address_line_1=customer.address_line_1,
                    delivery_address_line_2=customer.address_line_2,
                    delivery_city=customer.city,
                    delivery_postal_code=customer.postal_code,
                    delivery_landmark=customer.landmark,
                    delivery_notes="Please call before delivery.",
                    delivery_latitude=None,
                    delivery_longitude=None,
                ),
            )

            updated = order_service.update(
                created.id,
                OrderUpdate(
                    status=status,
                    payment_status=payment_status,
                    scheduled_delivery_date=scheduled,
                    requested_delivery_date=requested,
                ),
            )

            status_counter[updated.status.value] += 1

            order_model = db.get(Order, updated.id)
            if order_model is not None:
                lead_days = rng.randint(2, 11)
                created_at = datetime.combine(
                    requested - timedelta(days=lead_days),
                    datetime.min.time(),
                    tzinfo=UTC,
                ) + timedelta(hours=rng.randint(8, 21), minutes=rng.randint(0, 59))
                order_model.created_at = created_at
                order_model.updated_at = created_at + timedelta(hours=rng.randint(1, 48))

                for event in order_model.status_events:
                    if isinstance(event, OrderStatusEvent):
                        event.created_at = order_model.updated_at

                if order_model.status == OrderStatus.DELIVERED:
                    order_model.delivered_at = datetime.combine(
                        scheduled,
                        datetime.min.time(),
                        tzinfo=UTC,
                    ) + timedelta(hours=13)
                    order_model.ready_at = order_model.delivered_at - timedelta(hours=2)
                    order_model.preparing_at = order_model.delivered_at - timedelta(hours=18)
                    order_model.confirmed_at = order_model.created_at + timedelta(hours=2)
                elif order_model.status == OrderStatus.PREPARING:
                    order_model.preparing_at = datetime.now(UTC) - timedelta(hours=6)
                    order_model.confirmed_at = order_model.created_at + timedelta(hours=2)
                elif order_model.status == OrderStatus.READY:
                    order_model.ready_at = datetime.now(UTC) - timedelta(hours=3)
                    order_model.preparing_at = datetime.now(UTC) - timedelta(hours=10)
                    order_model.confirmed_at = order_model.created_at + timedelta(hours=2)
                elif order_model.status == OrderStatus.CONFIRMED:
                    order_model.confirmed_at = order_model.created_at + timedelta(hours=2)
                elif order_model.status == OrderStatus.CANCELLED:
                    order_model.cancelled_at = order_model.created_at + timedelta(hours=12)

                db.add(order_model)
                db.commit()

            past_order_ids.append(updated.id)

    # Future orders for upcoming Saturday production testing.
    next_saturdays: list[date] = []
    cursor = today
    while len(next_saturdays) < 8:
        if cursor.weekday() == 5:
            next_saturdays.append(cursor)
        cursor += timedelta(days=1)

    future_count = rng.randint(10, 20)
    for _ in range(future_count):
        customer = rng.choice(customers)
        scheduled = rng.choice(next_saturdays)
        requested = scheduled
        product_lines, collection_lines = choose_lines_for_order(rng, product_ids, collection_ids)

        source = weighted_choice(
            rng,
            [
                (OrderSource.WHATSAPP, 34),
                (OrderSource.WEBSITE, 24),
                (OrderSource.INSTAGRAM, 16),
                (OrderSource.FACEBOOK, 12),
                (OrderSource.WALK_IN, 8),
                (OrderSource.PHONE, 4),
                (OrderSource.MANUAL, 2),
            ],
        )

        status = weighted_choice(
            rng,
            [
                (OrderStatus.CONFIRMED, 56),
                (OrderStatus.PREPARING, 20),
                (OrderStatus.READY, 10),
                (OrderStatus.PENDING, 14),
            ],
        )
        method = weighted_choice(
            rng,
            [
                (PaymentMethod.CASH_ON_DELIVERY, 44),
                (PaymentMethod.BANK_TRANSFER, 30),
                (PaymentMethod.MANUAL, 20),
                (PaymentMethod.STRIPE, 6),
            ],
        )
        pay_status = weighted_choice(
            rng,
            [
                (PaymentStatus.PENDING, 75),
                (PaymentStatus.PAID, 23),
                (PaymentStatus.FAILED, 2),
            ],
        )

        created = order_service.create(
            OrderCreate(
                customer_id=customer.id,
                delivery_area_id=delivery_area_ids[weighted_choice(rng, [("Peradeniya", 20), ("Kandy", 20), ("Katugastota", 15), ("Kundasale", 10), ("Akurana", 10), ("Gampola", 10), ("Pickup Only", 15)])],
                source=source,
                payment_method=method,
                payment_status=pay_status,
                status=OrderStatus.PENDING,
                customer_notes="Upcoming scheduled order.",
                internal_notes="Future batch load test order.",
                requested_delivery_date=requested,
                product_lines=product_lines,
                collection_lines=collection_lines,
                delivery_contact_name=f"{customer.first_name} {customer.last_name}",
                delivery_phone_primary=customer.phone,
                delivery_phone_secondary=None,
                delivery_address_line_1=customer.address_line_1,
                delivery_address_line_2=customer.address_line_2,
                delivery_city=customer.city,
                delivery_postal_code=customer.postal_code,
                delivery_landmark=customer.landmark,
                delivery_notes="Future delivery slot.",
                delivery_latitude=None,
                delivery_longitude=None,
            ),
        )

        updated = order_service.update(
            created.id,
            OrderUpdate(
                status=status,
                payment_status=pay_status,
                scheduled_delivery_date=scheduled,
                requested_delivery_date=requested,
            ),
        )
        status_counter[updated.status.value] += 1
        future_order_ids.append(updated.id)

    return len(past_order_ids), len(future_order_ids), dict(status_counter)


def seed_production_and_procurement(db: Session, rng: random.Random) -> tuple[int, int]:
    batch_service = ProductionBatchService(db)
    purchase_service = PurchasePlanningService(db)

    delivery_dates = list(
        db.scalars(
            select(Order.scheduled_delivery_date)
            .where(Order.status.in_([
                OrderStatus.PENDING,
                OrderStatus.CONFIRMED,
                OrderStatus.PREPARING,
                OrderStatus.READY,
                OrderStatus.DELIVERED,
            ]))
            .distinct()
            .order_by(Order.scheduled_delivery_date.asc()),
        ).all(),
    )

    batch_count = 0
    purchase_updates = 0
    today = date.today()

    for delivery_date in delivery_dates:
        batch = batch_service.get_or_create_for_date(delivery_date, auto_create=True)
        batch_count += 1

        if delivery_date < today:
            status = ProductionBatchStatus.READY
            notes = "Historical batch completed."
        elif delivery_date <= today + timedelta(days=14):
            status = ProductionBatchStatus.PLANNING
            notes = "Upcoming batch in planning."
        else:
            status = ProductionBatchStatus.DRAFT
            notes = "Future batch draft created from order schedule."

        batch_service.update(
            batch.id,
            ProductionBatchUpdate(status=status, notes=notes),
        )

        lines = purchase_service.get_purchase_plan_lines(delivery_date)
        for line in lines:
            if delivery_date < today:
                pp_status = weighted_choice(
                    rng,
                    [
                        (PurchasePlanningStatus.ORDERED, 72),
                        (PurchasePlanningStatus.PLANNED, 24),
                        (PurchasePlanningStatus.NOT_PLANNED, 4),
                    ],
                )
            else:
                pp_status = weighted_choice(
                    rng,
                    [
                        (PurchasePlanningStatus.PLANNED, 46),
                        (PurchasePlanningStatus.ORDERED, 28),
                        (PurchasePlanningStatus.NOT_PLANNED, 26),
                    ],
                )

            purchase_service.update_purchase_status(
                PurchasePlanStatusUpdate(
                    delivery_date=delivery_date,
                    product_item_id=line.product_item_id,
                    purchase_status=pp_status,
                ),
            )
            purchase_updates += 1

    return batch_count, purchase_updates


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed realistic business data")
    parser.add_argument(
        "--skip-clear",
        action="store_true",
        help="Do not clear existing business data before seeding.",
    )
    args = parser.parse_args()

    rng = random.Random(RNG_SEED)

    db = SessionLocal()
    try:
        clear_counts: dict[str, int] = {}
        if not args.skip_clear:
            clear_counts = clear_business_data(db)

        # Ensure utility/labour/tax charges remain empty as required.
        for table_name in ("utility_charges", "labour_charges", "tax_charges"):
            if table_name in {t.name for t in Base.metadata.sorted_tables}:
                db.execute(delete(Base.metadata.tables[table_name]))
        db.commit()

        item_types = ensure_product_item_types(db)
        supplier_ids = seed_suppliers(db)
        product_item_ids = seed_product_items(db, item_types, supplier_ids)
        category_ids = ensure_product_categories(db)
        product_ids = seed_products(db, product_item_ids, category_ids)
        ensure_collection_packages(db)
        collection_ids = seed_collections(db, category_ids, product_item_ids["Cookie Box"])

        settings_service = BusinessSettingService(db)
        settings_service.update_settings(
            BusinessSettingsUpdate(
                delivery_fee=Decimal("500"),
                order_cutoff_day=Weekday.THURSDAY,
                delivery_day=Weekday.SATURDAY,
            ),
        )

        delivery_area_ids = seed_delivery_areas(db)
        customers = seed_customers(db, rng, count=50)

        historical_orders, future_orders, status_counts = create_orders(
            db,
            rng,
            customers,
            product_ids,
            collection_ids,
            delivery_area_ids,
        )
        batch_count, purchase_updates = seed_production_and_procurement(db, rng)

        print("\nRealistic business data seeding complete.")
        print(f"- Cleared tables: {len(clear_counts)}")
        if clear_counts:
            print("- Rows deleted by table:")
            for name, count in clear_counts.items():
                print(f"  * {name}: {count}")

        print(f"- Product item types created: {len(item_types)}")
        print(f"- Product items created: {len(product_item_ids)}")
        print(f"- Suppliers created: {len(supplier_ids)}")
        print(f"- Products created: {len(product_ids)}")
        print(f"- Collections created: {len(collection_ids)}")
        print(f"- Delivery areas created: {len(delivery_area_ids)}")
        print(f"- Customers created: {len(customers)}")
        print(f"- Historical orders created: {historical_orders}")
        print(f"- Future orders created: {future_orders}")
        print(f"- Total orders created: {historical_orders + future_orders}")
        print(f"- Production batches created/ensured: {batch_count}")
        print(f"- Purchase planning updates applied: {purchase_updates}")
        print("- Order status distribution:")
        for key in sorted(status_counts.keys()):
            print(f"  * {key}: {status_counts[key]}")

        print("\nNotes:")
        print("- Utility/Labour/Tax charge tables were intentionally kept empty.")
        print("- Product model has no premium boolean field; premium is captured in seeded descriptions.")
        print("- Product item model currently has no inventory-tracking flag column.")

        return 0
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        traceback.print_exc()
        print(f"Seeding failed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
