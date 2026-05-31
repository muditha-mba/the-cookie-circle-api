"""Seed development database with required baseline data."""

import argparse
import sys

from app.core.enums import UserRole
from app.core.security import hash_password
from app.database.session import SessionLocal
from app.repositories.user_repository import UserRepository
from app.utils.email import normalize_email
from app.utils.password import validate_password_strength

DEFAULT_ADMIN_EMAIL = "admin@thecookiecircle.lk"
DEFAULT_ADMIN_PASSWORD = "CookieCircle123!"
DEFAULT_ADMIN_FIRST_NAME = "Admin"

DEFAULT_CUSTOMER_EMAIL = "customer@thecookiecircle.lk"
DEFAULT_CUSTOMER_PASSWORD = "CookieCircle123!"
DEFAULT_CUSTOMER_FIRST_NAME = "Customer"
DEFAULT_CUSTOMER_LAST_NAME = "Demo"


def seed_admin(
    *,
    email: str = DEFAULT_ADMIN_EMAIL,
    password: str = DEFAULT_ADMIN_PASSWORD,
    first_name: str = DEFAULT_ADMIN_FIRST_NAME,
    last_name: str | None = None,
) -> bool:
    """Create the development admin user if it does not exist."""
    normalized_email = normalize_email(email)
    db = SessionLocal()
    try:
        users = UserRepository(db)
        existing = users.get_by_email(normalized_email)
        if existing:
            print(f"Admin user already exists: {existing.email}")
            return False

        user = users.create(
            email=normalized_email,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            first_name=first_name,
            last_name=last_name,
            email_verified=True,
        )
        db.commit()
        print(f"Admin user created: {user.email} ({user.id})")
        return True
    finally:
        db.close()


def seed_customer(
    *,
    email: str = DEFAULT_CUSTOMER_EMAIL,
    password: str = DEFAULT_CUSTOMER_PASSWORD,
    first_name: str = DEFAULT_CUSTOMER_FIRST_NAME,
    last_name: str | None = DEFAULT_CUSTOMER_LAST_NAME,
) -> bool:
    """Create a development customer user if it does not exist."""
    normalized_email = normalize_email(email)
    db = SessionLocal()
    try:
        users = UserRepository(db)
        existing = users.get_by_email(normalized_email)
        if existing:
            print(f"Customer user already exists: {existing.email}")
            return False

        user = users.create(
            email=normalized_email,
            password_hash=hash_password(password),
            role=UserRole.CUSTOMER,
            first_name=first_name,
            last_name=last_name,
            email_verified=True,
        )
        db.commit()
        print(f"Customer user created: {user.email} ({user.id})")
        return True
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed development database")
    parser.add_argument(
        "--email",
        default=DEFAULT_ADMIN_EMAIL,
        help="Admin email address",
    )
    parser.add_argument(
        "--password",
        default=DEFAULT_ADMIN_PASSWORD,
        help="Admin password (development only)",
    )
    parser.add_argument(
        "--first-name",
        default=DEFAULT_ADMIN_FIRST_NAME,
        help="Admin first name",
    )
    parser.add_argument("--last-name", default=None, help="Admin last name")
    parser.add_argument(
        "--customer-email",
        default=DEFAULT_CUSTOMER_EMAIL,
        help="Customer email address",
    )
    parser.add_argument(
        "--customer-password",
        default=DEFAULT_CUSTOMER_PASSWORD,
        help="Customer password (development only)",
    )
    parser.add_argument(
        "--customer-first-name",
        default=DEFAULT_CUSTOMER_FIRST_NAME,
        help="Customer first name",
    )
    parser.add_argument(
        "--customer-last-name",
        default=DEFAULT_CUSTOMER_LAST_NAME,
        help="Customer last name",
    )
    parser.add_argument(
        "--skip-customer",
        action="store_true",
        help="Only seed the admin user",
    )
    args = parser.parse_args()

    try:
        validate_password_strength(args.password)
        if not args.skip_customer:
            validate_password_strength(args.customer_password)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    admin_email = normalize_email(args.email)
    seed_admin(
        email=admin_email,
        password=args.password,
        first_name=args.first_name,
        last_name=args.last_name,
    )

    customer_email = normalize_email(args.customer_email)
    if not args.skip_customer:
        seed_customer(
            email=customer_email,
            password=args.customer_password,
            first_name=args.customer_first_name,
            last_name=args.customer_last_name,
        )

    print("\nDevelopment admin credentials:")
    print(f"  Email:    {admin_email}")
    print(f"  Password: {args.password}")
    print("  Login:    http://localhost:3001/login")

    if not args.skip_customer:
        print("\nDevelopment customer credentials:")
        print(f"  Email:    {customer_email}")
        print(f"  Password: {args.customer_password}")
        print("  Login:    http://localhost:3000/login")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
