"""Marketing attribution resolution tests."""

from app.core.enums import MarketingSource
from app.schemas.attribution import MarketingAttributionInput
from app.utils.marketing_attribution import resolve_marketing_attribution


def test_resolve_from_utm_source_instagram() -> None:
    resolved = resolve_marketing_attribution(
        MarketingAttributionInput(utm_source="instagram", utm_medium="social"),
    )
    assert resolved.source == MarketingSource.INSTAGRAM
    assert resolved.resolution == "utm_source"


def test_resolve_from_referrer_when_no_utm() -> None:
    resolved = resolve_marketing_attribution(
        MarketingAttributionInput(
            referrer="https://l.instagram.com/u/abc",
            landing_path="/collections",
        ),
    )
    assert resolved.source == MarketingSource.INSTAGRAM
    assert resolved.resolution == "referrer"


def test_utm_takes_priority_over_referrer() -> None:
    resolved = resolve_marketing_attribution(
        MarketingAttributionInput(
            utm_source="google",
            referrer="https://instagram.com/",
        ),
    )
    assert resolved.source == MarketingSource.GOOGLE


def test_unknown_utm_maps_to_other() -> None:
    resolved = resolve_marketing_attribution(
        MarketingAttributionInput(utm_source="some_new_blog"),
    )
    assert resolved.source == MarketingSource.OTHER
