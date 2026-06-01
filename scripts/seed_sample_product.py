"""Seed a sample product with recipe for development."""

import sys
from decimal import Decimal

from app.database.session import SessionLocal
from app.models.labour_charge import LabourCharge
from app.models.product import Product
from app.models.product_recipe_line import ProductRecipeLine
from app.models.product_item import ProductItem
from app.models.tax_charge import TaxCharge
from app.models.utility_charge import UtilityCharge
from app.repositories.product_repository import ProductRepository


def main() -> int:
    db = SessionLocal()
    products = ProductRepository(db)

    try:
        if products.get_by_name("Classic Butter Cookie"):
            print("Sample product already exists.")
            return 0

        from sqlalchemy import select

        butter = db.scalar(select(ProductItem).where(ProductItem.name == "Butter"))
        sugar = db.scalar(select(ProductItem).where(ProductItem.name == "Sugar"))
        if not butter or not sugar:
            print("Run seed_product_foundation.py first.", file=sys.stderr)
            return 1

        electricity = db.scalar(
            select(UtilityCharge).where(UtilityCharge.name == "Electricity"),
        )
        prep_labour = db.scalar(
            select(LabourCharge).where(LabourCharge.name == "Preparation Labour"),
        )
        vat = db.scalar(select(TaxCharge).where(TaxCharge.name == "VAT"))

        product = Product(
            name="Classic Butter Cookie",
            description="Sample butter cookie for development costing.",
            selling_price=Decimal("450"),
            buffer_amount=Decimal("10"),
            yield_quantity=Decimal("30"),
            production_notes="Bake at 180°C for 12 minutes. Rest dough for 2 hours.",
            is_active=True,
        )

        product.recipe_lines = [
            ProductRecipeLine(product_item_id=butter.id, quantity=Decimal("250")),
            ProductRecipeLine(product_item_id=sugar.id, quantity=Decimal("60")),
        ]

        if electricity:
            product.utility_charges = [electricity]
        if prep_labour:
            product.labour_charges = [prep_labour]
        if vat:
            product.tax_charges = [vat]

        products.create(product)
        db.commit()
        print(f"Created sample product: {product.name} ({product.id})")
        return 0
    except Exception as exc:
        db.rollback()
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
