"""Utility script to create an admin user manually."""

import argparse
import getpass
import sys

from app.core.enums import AdminRole, UserRole
from app.core.security import hash_password
from app.database.session import SessionLocal
from app.repositories.user_repository import UserRepository
from app.utils.email import normalize_email
from app.utils.password import validate_password_strength


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an admin user")
    parser.add_argument("--email", required=True, help="Admin email address")
    parser.add_argument("--first-name", default=None, help="Optional first name")
    parser.add_argument("--last-name", default=None, help="Optional last name")
    parser.add_argument(
        "--admin-role",
        choices=[AdminRole.SUPER_ADMIN.value, AdminRole.CLERK_ADMIN.value],
        default=AdminRole.SUPER_ADMIN.value,
        help="Admin access tier (default: super_admin)",
    )
    args = parser.parse_args()

    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match.", file=sys.stderr)
        return 1

    try:
        validate_password_strength(password)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    email = normalize_email(args.email)

    db = SessionLocal()
    try:
        users = UserRepository(db)
        if users.get_by_email(email):
            print("A user with this email already exists.", file=sys.stderr)
            return 1

        admin_role = AdminRole(args.admin_role)
        user = users.create(
            email=email,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            admin_role=admin_role,
            first_name=args.first_name,
            last_name=args.last_name,
            email_verified=True,
        )
        db.commit()
        print(f"Admin user created: {user.email} ({user.id}) [{admin_role.value}]")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
