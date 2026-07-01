"""Tests for GA4 Measurement Protocol service."""

from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.core.enums import OrderType, PaymentMethod, PaymentStatus
from app.services.ga4_measurement_protocol_service import Ga4MeasurementProtocolService


def _order() -> MagicMock:
    order = MagicMock()
    order.id = uuid4()
    order.order_number = "TCC-2026-0001"
    order.order_type = OrderType.WEEKLY_DELIVERY
    order.payment_method = PaymentMethod.ONLINE_CARD
    order.payment_status = PaymentStatus.PAID
    order.total_revenue_snapshot = Decimal("4500.00")
    return order


@patch("app.services.ga4_measurement_protocol_service.settings")
def test_send_purchase_noop_when_disabled(mock_settings) -> None:
    mock_settings.ga4_measurement_id = ""
    mock_settings.ga4_api_secret = ""

    with patch("app.services.ga4_measurement_protocol_service.httpx.post") as mock_post:
        Ga4MeasurementProtocolService.send_purchase(_order())
        mock_post.assert_not_called()


@patch("app.services.ga4_measurement_protocol_service.settings")
@patch("app.services.ga4_measurement_protocol_service.httpx.post")
def test_send_purchase_posts_event(mock_post, mock_settings) -> None:
    mock_settings.ga4_measurement_id = "G-TEST123"
    mock_settings.ga4_api_secret = "secret-value"
    mock_post.return_value.raise_for_status = MagicMock()

    order = _order()
    Ga4MeasurementProtocolService.send_purchase(order)

    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["json"]["events"][0]["name"] == "purchase"
    assert (
        call_kwargs["json"]["events"][0]["params"]["transaction_id"]
        == order.order_number
    )
    assert call_kwargs["json"]["events"][0]["params"]["value"] == 4500.0
    assert "measurement_id=G-TEST123" in mock_post.call_args.args[0]
    assert "api_secret=secret-value" in mock_post.call_args.args[0]
