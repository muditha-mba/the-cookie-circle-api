"""Send GA4 events via the Measurement Protocol (server-side)."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

import httpx

from app.core.config import settings
from app.models.order import Order

logger = logging.getLogger(__name__)

_GA4_COLLECT_URL = "https://www.google-analytics.com/mp/collect"


class Ga4MeasurementProtocolService:
    """Fire server-side GA4 conversion events after payment confirmation."""

    @staticmethod
    def is_enabled() -> bool:
        return bool(
            settings.ga4_measurement_id.strip()
            and settings.ga4_api_secret.strip()
        )

    @classmethod
    def send_purchase(cls, order: Order) -> None:
        """Send a purchase event. No-op when GA4 env vars are unset."""
        if not cls.is_enabled():
            return

        payload = cls._build_purchase_payload(order)
        cls._post(payload, event_name="purchase", order_number=order.order_number)

    @classmethod
    def _build_purchase_payload(cls, order: Order) -> dict[str, Any]:
        value = float(order.total_revenue_snapshot.quantize(Decimal("0.01")))
        return {
            "client_id": cls._client_id_for_order(order.id),
            "events": [
                {
                    "name": "purchase",
                    "params": {
                        "transaction_id": order.order_number,
                        "value": value,
                        "currency": "LKR",
                        "order_type": order.order_type.value,
                        "payment_type": order.payment_method.value,
                    },
                }
            ],
        }

    @staticmethod
    def _client_id_for_order(order_id: UUID) -> str:
        # Stable, non-PII identifier for server-side deduplication stitching.
        return f"server.order.{order_id}"

    @classmethod
    def _post(cls, payload: dict[str, Any], *, event_name: str, order_number: str) -> None:
        url = (
            f"{_GA4_COLLECT_URL}"
            f"?measurement_id={settings.ga4_measurement_id.strip()}"
            f"&api_secret={settings.ga4_api_secret.strip()}"
        )

        try:
            response = httpx.post(url, json=payload, timeout=5.0)
            response.raise_for_status()
            logger.info(
                "GA4 %s event sent for order_number=%s status=%s",
                event_name,
                order_number,
                response.status_code,
            )
        except Exception:
            logger.exception(
                "GA4 %s event failed for order_number=%s",
                event_name,
                order_number,
            )
