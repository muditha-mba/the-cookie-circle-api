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

    frontend_client_url: str = Field(
        default="http://localhost:3000",
        alias="FRONTEND_CLIENT_URL",
    )
    frontend_admin_url: str = Field(
        default="http://localhost:3001",
        alias="FRONTEND_ADMIN_URL",
    )

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
        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()
