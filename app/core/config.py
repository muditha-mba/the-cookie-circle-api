"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET_KEY = "change-me-in-production-use-a-long-random-secret"


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

        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()
