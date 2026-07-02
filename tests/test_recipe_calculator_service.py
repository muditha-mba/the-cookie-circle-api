"""Tests for recipe calculator scaling logic."""

from decimal import Decimal

from app.services.recipe_calculator_service import suggest_discrete_quantity
from app.utils.units import is_discrete_unit


def test_is_discrete_unit_for_count_packaging():
    assert is_discrete_unit("units") is True
    assert is_discrete_unit("Pieces") is True
    assert is_discrete_unit("packs") is True


def test_is_discrete_unit_for_mass_and_volume():
    assert is_discrete_unit("grams") is False
    assert is_discrete_unit("millilitres") is False
    assert is_discrete_unit("cups") is False


def test_suggest_discrete_quantity_rounds_small_fractions_up_to_one():
    assert suggest_discrete_quantity(Decimal("0.67")) == 1
    assert suggest_discrete_quantity(Decimal("0.30")) == 1


def test_suggest_discrete_quantity_rounds_to_nearest_whole():
    assert suggest_discrete_quantity(Decimal("1.33")) == 1
    assert suggest_discrete_quantity(Decimal("1.50")) == 2
    assert suggest_discrete_quantity(Decimal("2.49")) == 2


def test_suggest_discrete_quantity_zero_for_non_positive():
    assert suggest_discrete_quantity(Decimal("0")) == 0
    assert suggest_discrete_quantity(Decimal("-1")) == 0
