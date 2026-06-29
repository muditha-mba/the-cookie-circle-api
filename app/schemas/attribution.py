"""Marketing attribution payloads from the client website."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class MarketingAttributionInput(BaseModel):
    """First-touch acquisition context captured in the browser."""

    utm_source: str | None = Field(default=None, max_length=120)
    utm_medium: str | None = Field(default=None, max_length=120)
    utm_campaign: str | None = Field(default=None, max_length=120)
    utm_content: str | None = Field(default=None, max_length=120)
    utm_term: str | None = Field(default=None, max_length=120)
    referrer: str | None = Field(default=None, max_length=2000)
    landing_path: str | None = Field(default=None, max_length=500)
    captured_at: datetime | None = None

    @field_validator(
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_content",
        "utm_term",
        "referrer",
        "landing_path",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        stripped = value.strip()
        return stripped or None

    def has_signal(self) -> bool:
        """Whether the payload contains enough data to attempt resolution."""
        if self.utm_source:
            return True
        return bool(self.referrer)
