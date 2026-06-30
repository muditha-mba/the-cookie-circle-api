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

## Security

### Admin bootstrap

Create the first admin user with the CLI — never expose admin registration on a public route:

```bash
uv run python scripts/create_admin.py
```

### Production checklist

Before deploying with `APP_ENV=production`:

1. Set a strong `JWT_SECRET_KEY` (32+ random characters).
2. Set `DEBUG=false`.
3. Configure `EMAIL_PROVIDER=resend` with `RESEND_API_KEY` and `EMAIL_FROM`
   (verify `thecookiecircle.lk` in Resend and add DNS records first).
4. Set `TRUSTED_HOSTS` to your API hostname.
5. Restrict `CORS_ORIGINS` to the client and admin domains.
6. Terminate HTTPS at your reverse proxy and enable `RATE_LIMIT_TRUST_PROXY=true` when the proxy sets `X-Forwarded-For`.
7. Optionally restrict admin API access with `ADMIN_ALLOWED_IPS`.
8. Optionally enable Turnstile with `TURNSTILE_SECRET_KEY` and `CAPTCHA_REQUIRED=true`.
9. Run database migrations, including `027_user_token_version`.
10. Store secrets in your host environment or secrets manager — never commit `.env`.
11. Configure production database backups — see [DATABASE_BACKUP.md](./DATABASE_BACKUP.md).

### Session invalidation

- `POST /api/v1/auth/logout` revokes the current refresh token.
- `POST /api/v1/auth/logout-all` revokes all refresh tokens and invalidates outstanding access tokens immediately.
- Password reset and password change also invalidate existing sessions.

### Email (Resend)

Transactional email is sent from the API only (verification, password reset, welcome,
order confirmation). Configure per environment:

```bash
EMAIL_PROVIDER=resend
RESEND_API_KEY=re_xxxxxxxx
EMAIL_FROM=The Cookie Circle <hello@thecookiecircle.lk>
EMAIL_REPLY_TO=hello@thecookiecircle.lk
FRONTEND_CLIENT_URL=https://thecookiecircle.lk
```

- **Development:** use `EMAIL_PROVIDER=resend` with a real key to test delivery, or
  `EMAIL_PROVIDER=console` when no key is set.
- **Staging / production:** `EMAIL_PROVIDER=resend` is required; subjects are prefixed
  with `[Staging]` or `[Dev]` automatically by environment.
- Verify `thecookiecircle.lk` in Resend and add DNS (SPF/DKIM) before sending to customers.
- `ORDER_NOTIFICATION_EMAIL` sends an internal alert to your team inbox (default:
  `hello@thecookiecircle.lk`) whenever a new order is created. Set empty to disable.

### Security audit logs

Structured security events are written to the `security.audit` logger (JSON lines). Configure your log collector to monitor:

- `login_failed`
- `rate_limit_exceeded`
- `refresh_token_reuse_detected`
- `admin_mutation`
- `logout_all_sessions`
- `password_changed`
