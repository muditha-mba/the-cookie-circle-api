"""Seed default global cost charges for development."""

import sys
from decimal import Decimal

from app.core.enums import ChargeApplicability, ChargeType
from app.database.session import SessionLocal
from app.repositories.charge_repository import ChargeRepository
from app.models.labour_charge import LabourCharge
from app.models.tax_charge import TaxCharge
from app.models.utility_charge import UtilityCharge

# name, description, charge_type, amount, applicability
UTILITIES = [
    ("Electricity", "Monthly electricity", ChargeType.FIXED, Decimal("500"), ChargeApplicability.PRODUCT),
    ("Water", "Monthly water", ChargeType.FIXED, Decimal("200"), ChargeApplicability.BOTH),
    ("Gas", "Monthly gas", ChargeType.FIXED, Decimal("150"), ChargeApplicability.BOTH),
    ("Internet", "Monthly internet", ChargeType.FIXED, Decimal("350"), ChargeApplicability.BOTH),
]

LABOUR = [
    ("Preparation Labour", "Cookie preparation labour", ChargeType.FIXED, Decimal("800"), ChargeApplicability.PRODUCT),
    ("Packaging Labour", "Packaging labour", ChargeType.FIXED, Decimal("400"), ChargeApplicability.COLLECTION),
    ("Administration Labour", "Admin overhead labour", ChargeType.FIXED, Decimal("600"), ChargeApplicability.BOTH),
]

TAXES = [
    ("VAT", "Value added tax", ChargeType.PERCENTAGE, Decimal("18"), ChargeApplicability.BOTH),
    ("Delivery Tax", "Delivery tax", ChargeType.PERCENTAGE, Decimal("5"), ChargeApplicability.COLLECTION),
    ("Marketplace Fee", "Marketplace commission", ChargeType.PERCENTAGE, Decimal("30"), ChargeApplicability.BOTH),
]


def seed_table(repo: ChargeRepository, rows: list) -> None:
    for name, description, charge_type, amount, applicability in rows:
        if repo.get_by_name(name):
            print(f"Already exists: {name}")
            continue
        repo.create(
            name=name,
            description=description,
            charge_type=charge_type,
            amount=amount,
            applicability=applicability,
            is_active=True,
        )
        print(f"Created: {name}")


def main() -> int:
    db = SessionLocal()
    try:
        seed_table(ChargeRepository(db, UtilityCharge), UTILITIES)
        seed_table(ChargeRepository(db, LabourCharge), LABOUR)
        seed_table(ChargeRepository(db, TaxCharge), TAXES)
        db.commit()
        print("\nGlobal cost seed complete.")
        return 0
    except Exception as exc:
        db.rollback()
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
