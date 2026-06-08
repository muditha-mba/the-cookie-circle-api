"""Health check response schemas."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response schema for the health check endpoint."""

    status: str = Field(examples=["healthy"])
