# Apply migrations to a remote database (Neon)

Migrations are **SQL scripts in this repo**. Git deploys the code to Render; **you** apply schema changes to Neon by running Alembic locally.

```
Local API project  →  alembic upgrade head  →  Neon (staging / production)
```

Render does **not** run migrations automatically.

---

## Prerequisites

- `uv` installed
- `DATABASE_URL` for the target environment (from **Render → Environment** or **Neon → Connection string**)
- URL must use: `postgresql+psycopg://...` (not plain `postgresql://`)

---

## Steps (same terminal session)

```bash
cd the-cookie-circle-api
uv sync
```

Set the database URL once for this terminal (replace with your real URL):

```bash
export DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST/neondb?sslmode=require"
```

Check current version:

```bash
uv run alembic current
```

Apply all pending migrations:

```bash
uv run alembic upgrade head
```

Confirm you are at the latest:

```bash
uv run alembic current
```

Expected last line: `046_... (head)` (revision number changes as new migrations are added).

---

## Optional checks

Latest migration in the repo:

```bash
uv run alembic heads
```

Recent history:

```bash
uv run alembic history | tail -10
```

---

## Which database am I touching?

| `DATABASE_URL` from | Database |
|---------------------|----------|
| Render staging service env | Staging (Neon) |
| Render production service env | Production (Neon) |
| Local `.env` (localhost) | Local dev only |

Always run `alembic current` **before** `upgrade head` if you are unsure.

---

## Notes

- `export DATABASE_URL=...` lasts until you close the terminal. Open a new tab → export again.
- For migrations, only `DATABASE_URL` is required. You do not need full staging env vars if you export the URL alone.
- After `upgrade head`, test the API/admin feature that needed the schema change. Redeploy Render only if you also pushed new API code.

---

## Creating a new migration (developers)

After changing SQLAlchemy models:

```bash
uv run alembic revision --autogenerate -m "short_description"
```

Review the generated file in `alembic/versions/`, commit it, push, then run `upgrade head` on each remote database (staging first, then production).
