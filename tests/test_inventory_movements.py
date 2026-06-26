"""Tests for inventory movement quantity rules."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.core.enums import InventoryMovementReferenceType, InventoryMovementType
from app.core.exceptions import ValidationError
from app.services.inventory_movement_service import InventoryMovementService


def test_apply_quantity_change_rejects_negative_balance():
    service = InventoryMovementService(MagicMock())
    lot = SimpleNamespace(
        id="lot-id",
        quantity_on_hand=Decimal("5"),
        unit="grams",
        is_active=True,
    )
    service.movements = MagicMock()
    service.movements.create.side_effect = lambda movement: movement

    with pytest.raises(ValidationError, match="Insufficient quantity"):
        service._apply_quantity_change(
            lot=lot,
            quantity_change=Decimal("-10"),
            movement_type=InventoryMovementType.WASTE,
            reference_type=InventoryMovementReferenceType.MANUAL,
            reference_id=None,
            notes=None,
            user_id=None,
        )
