"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.core.config import settings
from app.middleware.cors import setup_cors
from app.routers.auth import router as auth_router
from app.routers.health import router as health_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Application startup and shutdown lifecycle."""
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )

    setup_cors(app)
    app.include_router(health_router)
    app.include_router(auth_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
