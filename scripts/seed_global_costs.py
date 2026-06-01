"""Seed default global cost charges for development."""

import sys
from decimal import Decimal

from app.core.enums import ChargeType
from app.database.session import SessionLocal
from app.repositories.charge_repository import ChargeRepository
from app.models.labour_charge import LabourCharge
from app.models.tax_charge import TaxCharge
from app.models.utility_charge import UtilityCharge

UTILITIES = [
    ("Electricity", "Monthly electricity", ChargeType.FIXED, Decimal("500")),
    ("Water", "Monthly water", ChargeType.FIXED, Decimal("200")),
    ("Gas", "Monthly gas", ChargeType.FIXED, Decimal("150")),
    ("Internet", "Monthly internet", ChargeType.FIXED, Decimal("350")),
]

LABOUR = [
    ("Preparation Labour", "Cookie preparation labour", ChargeType.FIXED, Decimal("800")),
    ("Packaging Labour", "Packaging labour", ChargeType.FIXED, Decimal("400")),
    ("Administration Labour", "Admin overhead labour", ChargeType.FIXED, Decimal("600")),
]

TAXES = [
    ("VAT", "Value added tax", ChargeType.PERCENTAGE, Decimal("18")),
    ("Delivery Tax", "Delivery tax", ChargeType.PERCENTAGE, Decimal("5")),
    ("Marketplace Fee", "Marketplace commission", ChargeType.PERCENTAGE, Decimal("30")),
]


def seed_table(repo: ChargeRepository, rows: list) -> None:
    for name, description, charge_type, amount in rows:
        if repo.get_by_name(name):
            print(f"Already exists: {name}")
            continue
        repo.create(
            name=name,
            description=description,
            charge_type=charge_type,
            amount=amount,
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
