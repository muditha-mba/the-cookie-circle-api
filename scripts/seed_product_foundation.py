"""Seed default product item types and sample product items for development."""

import sys
from decimal import Decimal

from app.database.session import SessionLocal
from app.repositories.product_item_repository import ProductItemRepository
from app.repositories.product_item_type_repository import ProductItemTypeRepository
DEFAULT_TYPES = [
    ("Ingredient", "Raw materials used in recipes"),
    ("Packaging", "Boxes, ribbons, and presentation materials"),
    ("Utility", "Electricity, water, gas, and internet"),
    ("Labour", "Preparation, packaging, and administration labour"),
    ("Tax", "VAT, delivery tax, and other taxes"),
]

SAMPLE_ITEMS = [
    ("Ingredient", "Butter", "1150", "500", "grams"),
    ("Ingredient", "Sugar", "450", "1000", "grams"),
    ("Packaging", "Cookie Box", "250", "1", "units"),
]


def main() -> int:
    db = SessionLocal()
    types_repo = ProductItemTypeRepository(db)
    items_repo = ProductItemRepository(db)

    try:
        type_by_name: dict[str, object] = {}
        for name, description in DEFAULT_TYPES:
            existing = types_repo.get_by_name(name)
            if existing:
                print(f"Type already exists: {name}")
                type_by_name[name] = existing
                continue
            created = types_repo.create(name=name, description=description, is_active=True)
            type_by_name[name] = created
            print(f"Created type: {name}")

        for type_name, item_name, price, qty, unit in SAMPLE_ITEMS:
            item_type = type_by_name.get(type_name)
            if item_type is None:
                item_type = types_repo.get_by_name(type_name)
            if item_type is None:
                print(f"Skipping {item_name}: type {type_name} not found", file=sys.stderr)
                continue

            if items_repo.get_by_name(item_name):
                print(f"Item already exists: {item_name}")
                continue

            items_repo.create(
                item_type_id=item_type.id,
                name=item_name,
                description=None,
                purchase_price=Decimal(price),
                purchase_quantity=Decimal(qty),
                purchase_unit=unit,
                is_active=True,
            )
            print(f"Created item: {item_name}")

        db.commit()
        print("\nProduct foundation seed complete.")
        return 0
    except Exception as exc:
        db.rollback()
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
