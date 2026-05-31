# The Cookie Circle API

Production-ready FastAPI foundation for The Cookie Circle ecosystem.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL 15+

## Setup

```bash
cp .env.example .env
uv sync
```

Update `.env` with your PostgreSQL connection string.

## Run

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Health Check

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{ "status": "healthy" }
```

## Migrations

Generate a migration:

```bash
uv run alembic revision --autogenerate -m "describe_changes"
```

Apply migrations:

```bash
uv run alembic upgrade head
```

## Project Structure

```
app/
├── core/           # Configuration and shared primitives
├── database/       # SQLAlchemy engine, session, base
├── models/         # SQLAlchemy models
├── schemas/        # Pydantic request/response schemas
├── services/       # Business logic
├── repositories/   # Data access layer
├── routers/        # API route handlers
├── middleware/     # HTTP middleware
├── utils/          # Shared utilities
└── main.py         # Application entry point
```
