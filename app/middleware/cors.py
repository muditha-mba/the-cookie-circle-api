"""CORS middleware configuration."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

DEFAULT_ALLOWED_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
DEFAULT_ALLOWED_HEADERS = [
    "Authorization",
    "Content-Type",
    "Accept",
    "Origin",
    "X-Requested-With",
]


def setup_cors(app: FastAPI) -> None:
    """Configure CORS for allowed frontend origins."""
    cors_kwargs: dict = {
        "allow_origins": settings.cors_origin_list,
        "allow_credentials": True,
        "allow_methods": DEFAULT_ALLOWED_METHODS,
        "allow_headers": DEFAULT_ALLOWED_HEADERS,
    }

    # Next.js may bind to an alternate port when the default is in use.
    if settings.is_development:
        cors_kwargs["allow_origin_regex"] = r"http://(localhost|127\.0\.0\.1)(:\d+)?"
        cors_kwargs["allow_methods"] = ["*"]
        cors_kwargs["allow_headers"] = ["*"]

    app.add_middleware(CORSMiddleware, **cors_kwargs)
