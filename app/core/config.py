"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET_KEY = "change-me-in-production-use-a-long-random-secret"

S3_BUCKET_BY_APP_ENV: dict[str, str] = {
    "development": "the-cookie-circle-dev-assets",
    "staging": "the-cookie-circle-staging-assets",
    "production": "the-cookie-circle-live-assets",
}


class Settings(BaseSettings):
    """Central configuration for the API."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="The Cookie Circle API", alias="APP_NAME")
    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        alias="APP_ENV",
    )
    debug: bool = Field(default=False, alias="DEBUG")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        alias="LOG_LEVEL",
    )

    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    database_url: PostgresDsn = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/cookie_circle_dev",
        alias="DATABASE_URL",
    )

    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:3001",
        alias="CORS_ORIGINS",
    )

    jwt_secret_key: str = Field(
        default=DEFAULT_JWT_SECRET_KEY,
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=15,
        alias="ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    refresh_token_expire_days: int = Field(
        default=7,
        alias="REFRESH_TOKEN_EXPIRE_DAYS",
    )
    email_verification_token_expire_hours: int = Field(
        default=24,
        alias="EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS",
    )
    password_reset_token_expire_hours: int = Field(
        default=1,
        alias="PASSWORD_RESET_TOKEN_EXPIRE_HOURS",
    )
    dev_email_verification_token: str | None = Field(
        default="dev-verify",
        alias="DEV_EMAIL_VERIFICATION_TOKEN",
        description=(
            "Development-only reusable verification token. "
            "Set to empty string to disable."
        ),
    )

    frontend_client_url: str = Field(
        default="http://localhost:3000",
        alias="FRONTEND_CLIENT_URL",
    )
    frontend_admin_url: str = Field(
        default="http://localhost:3001",
        alias="FRONTEND_ADMIN_URL",
    )

    whatsapp_business_phone: str = Field(
        default="94771234567",
        alias="WHATSAPP_BUSINESS_PHONE",
        description="E.164 digits only, no plus sign, for wa.me links",
    )

    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_trust_proxy: bool = Field(default=False, alias="RATE_LIMIT_TRUST_PROXY")

    trusted_hosts: str = Field(
        default="localhost,127.0.0.1",
        alias="TRUSTED_HOSTS",
        description="Comma-separated hostnames allowed by TrustedHostMiddleware",
    )

    admin_allowed_ips: str = Field(
        default="",
        alias="ADMIN_ALLOWED_IPS",
        description="Optional comma-separated admin API IP allowlist",
    )

    email_provider: Literal["console", "smtp", "resend"] = Field(
        default="console",
        alias="EMAIL_PROVIDER",
    )
    resend_api_key: str | None = Field(default=None, alias="RESEND_API_KEY")
    email_from: str | None = Field(
        default=None,
        alias="EMAIL_FROM",
        description='Sender address, e.g. "The Cookie Circle <hello@thecookiecircle.lk>"',
    )
    email_reply_to: str | None = Field(default=None, alias="EMAIL_REPLY_TO")
    order_notification_email: str | None = Field(
        default="hello@thecookiecircle.lk",
        alias="ORDER_NOTIFICATION_EMAIL",
        description="Internal inbox notified when a new order is created. Leave empty to disable.",
    )
    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str | None = Field(default=None, alias="SMTP_USERNAME")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_from_email: str | None = Field(default=None, alias="SMTP_FROM_EMAIL")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")

    turnstile_secret_key: str | None = Field(default=None, alias="TURNSTILE_SECRET_KEY")
    captcha_required: bool = Field(default=False, alias="CAPTCHA_REQUIRED")

    api_public_url: str = Field(
        default="http://localhost:8000",
        alias="API_PUBLIC_URL",
        description="Public API base URL used for stable media links served by the API",
    )

    # ── WebXPay payment gateway ────────────────────────────────────────────────
    webxpay_enabled: bool = Field(
        default=False,
        alias="WEBXPAY_ENABLED",
        description=(
            "Master switch. Must be true before online payment methods work at checkout. "
            "Keep false until merchant account credentials are confirmed and tested."
        ),
    )
    webxpay_sandbox: bool = Field(
        default=True,
        alias="WEBXPAY_SANDBOX",
        description="true = staging (stagingxpay.info), false = live (webxpay.com)",
    )
    webxpay_merchant_id: str | None = Field(
        default=None,
        alias="WEBXPAY_MERCHANT_ID",
        description="Merchant ID from WebXPay dashboard — used only for reference/logging",
    )
    webxpay_secret_key: str | None = Field(
        default=None,
        alias="WEBXPAY_SECRET_KEY",
        description="Secret key from WebXPay dashboard Settings > Integrations",
    )
    webxpay_public_key_pem: str | None = Field(
        default=None,
        alias="WEBXPAY_PUBLIC_KEY_PEM",
        description=(
            "WebXPay RSA public key (PEM format, newlines as \\n or actual newlines). "
            "Used to encrypt the payment blob sent to WebXPay and to verify return signatures."
        ),
    )
    webxpay_return_url: str | None = Field(
        default=None,
        alias="WEBXPAY_RETURN_URL",
        description=(
            "Return URL registered in WebXPay dashboard. "
            "WebXPay POSTs payment result to this URL after transaction completes. "
            "Must point to: {API_PUBLIC_URL}/api/v1/payments/webxpay/return"
        ),
    )
    webxpay_cancel_url: str | None = Field(
        default=None,
        alias="WEBXPAY_CANCEL_URL",
        description=(
            "Cancel URL shown to customer if they abandon the WebXPay payment page. "
            "Typically a frontend URL such as {FRONTEND_CLIENT_URL}/cart"
        ),
    )

    aws_access_key_id: str | None = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str | None = Field(default=None, alias="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="ap-southeast-1", alias="AWS_REGION")
    s3_bucket_name: str | None = Field(
        default=None,
        alias="S3_BUCKET_NAME",
        description="Optional override. Defaults to the bucket for APP_ENV when unset.",
    )
    s3_shared_memories_prefix: str = Field(
        default="shared-memories",
        alias="S3_SHARED_MEMORIES_PREFIX",
    )
    s3_reviews_prefix: str = Field(
        default="reviews",
        alias="S3_REVIEWS_PREFIX",
        description="S3 prefix reserved for future customer review image uploads",
    )
    s3_purchase_receipts_prefix: str = Field(
        default="purchase-receipts",
        alias="S3_PURCHASE_RECEIPTS_PREFIX",
        description="S3 prefix for supplier bill uploads on purchase receipts",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def webxpay_billing_url(self) -> str:
        """WebXPay hosted payment page URL — staging or live."""
        if self.webxpay_sandbox:
            return "https://stagingxpay.info/index.php?route=checkout/billing"
        return "https://webxpay.com/index.php?route=checkout/billing"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def resolved_s3_bucket_name(self) -> str | None:
        explicit = (self.s3_bucket_name or "").strip()
        if explicit:
            return explicit
        return S3_BUCKET_BY_APP_ENV.get(self.app_env)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def s3_enabled(self) -> bool:
        return bool(
            self.aws_access_key_id
            and self.aws_secret_access_key
            and self.resolved_s3_bucket_name,
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def trusted_host_list(self) -> list[str]:
        return [host.strip() for host in self.trusted_hosts.split(",") if host.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def admin_allowed_ip_list(self) -> list[str]:
        return [ip.strip() for ip in self.admin_allowed_ips.split(",") if ip.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_staging(self) -> bool:
        return self.app_env == "staging"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if self.app_env in ("production", "staging"):
            if (
                self.jwt_secret_key == DEFAULT_JWT_SECRET_KEY
                or len(self.jwt_secret_key) < 32
            ):
                raise ValueError(
                    "JWT_SECRET_KEY must be a secure random value of at least "
                    "32 characters in staging and production environments",
                )

        if self.app_env in ("production", "staging"):
            if self.email_provider == "resend":
                if not (self.resend_api_key or "").strip():
                    raise ValueError(
                        "RESEND_API_KEY is required when EMAIL_PROVIDER=resend "
                        f"and APP_ENV={self.app_env}",
                    )
                if not (self.email_from or "").strip():
                    raise ValueError(
                        "EMAIL_FROM is required when EMAIL_PROVIDER=resend "
                        f"and APP_ENV={self.app_env}",
                    )
            elif self.email_provider == "smtp":
                if not self.smtp_host or not self.smtp_from_email:
                    raise ValueError(
                        "SMTP_HOST and SMTP_FROM_EMAIL are required when "
                        f"EMAIL_PROVIDER=smtp and APP_ENV={self.app_env}",
                    )
            else:
                raise ValueError(
                    f"EMAIL_PROVIDER must be resend (recommended) or smtp when "
                    f"APP_ENV={self.app_env}",
                )

        if self.is_production and self.debug:
            raise ValueError("DEBUG must be false when APP_ENV=production")

        if self.captcha_required and not (self.turnstile_secret_key or "").strip():
            raise ValueError(
                "TURNSTILE_SECRET_KEY is required when CAPTCHA_REQUIRED=true",
            )

        if self.webxpay_enabled:
            missing = [
                name
                for name, value in {
                    "WEBXPAY_SECRET_KEY": self.webxpay_secret_key,
                    "WEBXPAY_PUBLIC_KEY_PEM": self.webxpay_public_key_pem,
                }.items()
                if not (value or "").strip()
            ]
            if missing:
                raise ValueError(
                    f"WEBXPAY_ENABLED=true requires these variables to be set: "
                    f"{', '.join(missing)}",
                )

        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()
