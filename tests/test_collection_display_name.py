"""Tests for customer-facing collection display names."""

from app.utils.collection_display_name import (
    format_collection_display_name,
    format_package_type_display_name,
)


def test_maps_legacy_size_names_to_customer_titles() -> None:
    assert (
        format_collection_display_name("The Party Circle")
        == "Chocolate Chip Cookie Collection"
    )
    assert (
        format_collection_display_name("The Family Circle")
        == "Chocolate Chip Cookie Collection"
    )
    assert (
        format_collection_display_name("The Gathering Circle")
        == "The Butter Cookie Collection"
    )


def test_maps_package_codes() -> None:
    assert (
        format_collection_display_name("Anything", package_code="MIX_AND_MATCH")
        == "Chocolate Chip Cookie Collection"
    )
    assert (
        format_collection_display_name("Anything", package_code="BUTTER_COLLECTION")
        == "The Butter Cookie Collection"
    )


def test_maps_package_type_display_names() -> None:
    assert (
        format_package_type_display_name("Mix and Match", package_code="MIX_AND_MATCH")
        == "Favourite Cookies"
    )
    assert (
        format_package_type_display_name("Butter Collection")
        == "Tea Time Cookies"
    )


def test_unknown_names_pass_through() -> None:
    assert format_collection_display_name("Custom Gift Box") == "Custom Gift Box"
