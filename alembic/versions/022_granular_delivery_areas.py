"""Replace coarse delivery zones with customer-facing localities.

Revision ID: 022_granular_delivery_areas
Revises: 021_delivery_area_from_city
"""

from decimal import Decimal
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "022_granular_delivery_areas"
down_revision: Union[str, None] = "021_delivery_area_from_city"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Locality name -> delivery fee inherited from the former operational zone.
GRANULAR_DELIVERY_AREAS: tuple[tuple[str, Decimal, bool], ...] = (
    ("Kandy", Decimal("700"), False),
    ("Asgiriya", Decimal("700"), False),
    ("Mulgampola", Decimal("700"), False),
    ("Bowalawatta", Decimal("700"), False),
    ("Peradeniya", Decimal("500"), False),
    ("Aniwatta", Decimal("500"), False),
    ("Kiribathkumbura", Decimal("500"), False),
    ("Pilimathalawa", Decimal("500"), False),
    ("Kadugannawa", Decimal("500"), False),
    ("Gelioya", Decimal("500"), False),
    ("Katugastota", Decimal("650"), False),
    ("Watapuluwa", Decimal("650"), False),
    ("Ampitiya", Decimal("750"), False),
    ("Tennekumbura", Decimal("750"), False),
    ("Kundasale", Decimal("750"), False),
    ("Akurana", Decimal("650"), False),
    ("Danture", Decimal("650"), False),
    ("Poththapitiya", Decimal("650"), False),
    ("Gampola", Decimal("800"), False),
    ("Pickup Only", Decimal("0"), True),
)

LEGACY_ZONE_NAMES: tuple[str, ...] = ("Kandy Central",)


def upgrade() -> None:
    connection = op.get_bind()

    for name, fee, pickup_only in GRANULAR_DELIVERY_AREAS:
        existing = connection.execute(
            sa.text("SELECT id FROM delivery_areas WHERE name = :name LIMIT 1"),
            {"name": name},
        ).fetchone()

        if existing is None:
            connection.execute(
                sa.text(
                    """
                    INSERT INTO delivery_areas (
                        id,
                        name,
                        description,
                        delivery_fee_override,
                        pickup_only,
                        is_active
                    )
                    VALUES (
                        gen_random_uuid(),
                        :name,
                        NULL,
                        :fee,
                        :pickup_only,
                        true
                    )
                    """
                ),
                {
                    "name": name,
                    "fee": fee,
                    "pickup_only": pickup_only,
                },
            )
        else:
            connection.execute(
                sa.text(
                    """
                    UPDATE delivery_areas
                    SET delivery_fee_override = :fee,
                        pickup_only = :pickup_only,
                        is_active = true
                    WHERE name = :name
                    """
                ),
                {
                    "name": name,
                    "fee": fee,
                    "pickup_only": pickup_only,
                },
            )

    connection.execute(
        sa.text(
            """
            UPDATE orders AS o
            SET delivery_area_id = da.id
            FROM delivery_areas AS da
            WHERE o.delivery_city IS NOT NULL
              AND btrim(o.delivery_city) <> ''
              AND da.name = btrim(o.delivery_city)
              AND da.is_active = true
            """
        )
    )

    for legacy_name in LEGACY_ZONE_NAMES:
        connection.execute(
            sa.text(
                """
                UPDATE delivery_areas
                SET is_active = false
                WHERE name = :name
                """
            ),
            {"name": legacy_name},
        )


def downgrade() -> None:
    connection = op.get_bind()

    for legacy_name in LEGACY_ZONE_NAMES:
        connection.execute(
            sa.text(
                """
                UPDATE delivery_areas
                SET is_active = true
                WHERE name = :name
                """
            ),
            {"name": legacy_name},
        )

    locality_names = tuple(
        name for name, _, pickup_only in GRANULAR_DELIVERY_AREAS if not pickup_only
    ) + ("Pickup Only",)
    connection.execute(
        sa.text(
            """
            UPDATE delivery_areas
            SET is_active = false
            WHERE name = ANY(:names)
              AND name NOT IN ('Peradeniya', 'Katugastota', 'Kundasale', 'Akurana', 'Gampola')
            """
        ),
        {"names": list(locality_names)},
    )
