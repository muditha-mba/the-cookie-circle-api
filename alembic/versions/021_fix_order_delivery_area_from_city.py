"""Align order delivery_area_id with delivery_city locality mapping.

Revision ID: 021_delivery_area_from_city
Revises: 020_order_reviews
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "021_delivery_area_from_city"
down_revision: Union[str, None] = "020_order_reviews"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COVERAGE_TO_OPERATIONAL_ZONE: dict[str, str] = {
    "Kandy": "Kandy Central",
    "Asgiriya": "Kandy Central",
    "Mulgampola": "Kandy Central",
    "Bowalawatta": "Kandy Central",
    "Peradeniya": "Peradeniya",
    "Aniwatta": "Peradeniya",
    "Kiribathkumbura": "Peradeniya",
    "Pilimathalawa": "Peradeniya",
    "Kadugannawa": "Peradeniya",
    "Gelioya": "Peradeniya",
    "Katugastota": "Katugastota",
    "Watapuluwa": "Katugastota",
    "Ampitiya": "Kundasale",
    "Tennekumbura": "Kundasale",
    "Kundasale": "Kundasale",
    "Akurana": "Akurana",
    "Danture": "Akurana",
    "Poththapitiya": "Akurana",
}


def _operational_zone_for_coverage(coverage_area: str) -> str | None:
    normalized = coverage_area.strip()
    if not normalized:
        return None

    for locality, zone in COVERAGE_TO_OPERATIONAL_ZONE.items():
        if locality.casefold() == normalized.casefold():
            return zone

    return None


def upgrade() -> None:
    connection = op.get_bind()

    area_rows = connection.execute(
        sa.text(
            """
            SELECT id, name
            FROM delivery_areas
            WHERE is_active = true
            """
        )
    ).fetchall()
    area_id_by_name = {row.name: row.id for row in area_rows}

    order_rows = connection.execute(
        sa.text(
            """
            SELECT id, delivery_city, delivery_area_id
            FROM orders
            WHERE delivery_city IS NOT NULL
              AND btrim(delivery_city) <> ''
            """
        )
    ).fetchall()

    for order in order_rows:
        zone_name = _operational_zone_for_coverage(order.delivery_city)
        if not zone_name:
            continue

        correct_area_id = area_id_by_name.get(zone_name)
        if correct_area_id is None or correct_area_id == order.delivery_area_id:
            continue

        connection.execute(
            sa.text(
                """
                UPDATE orders
                SET delivery_area_id = :delivery_area_id
                WHERE id = :order_id
                """
            ),
            {
                "delivery_area_id": correct_area_id,
                "order_id": order.id,
            },
        )


def downgrade() -> None:
    # Data correction only; previous incorrect values cannot be restored safely.
    pass
