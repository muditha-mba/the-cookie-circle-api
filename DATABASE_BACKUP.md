# Database backup & restore (production)

Backups protect **PostgreSQL data** (orders, customers, products, etc.). They are independent of Vercel custom domains — you can enable them while the client still runs on `*.vercel.app`.

| Environment | Strategy |
|-------------|----------|
| **Staging** | Neon built-in history only (~6 h on Free) — no S3 dumps |
| **Production** | Three layers below |

---

## Layer 1 — Neon PITR (built-in)

**What:** Point-in-time recovery inside Neon.

| Neon plan | Window |
|-----------|--------|
| Free | ~6 hours |
| Launch | 7 days (recommended when taking real orders) |

**Where:** [Neon console](https://console.neon.tech) → production project → **Branches** / **Restore**.

**Use when:** Recent mistake (bad update, accidental delete) within the PITR window.

**Setup:** No code. On Free, history is automatic. Upgrade production to **Launch** when you want 7-day recovery.

---

## Layer 2 — Nightly `pg_dump` → S3 (automated)

**What:** Logical backup uploaded to a **private** S3 bucket every night at 03:00 Asia/Colombo.

**Workflow:** `.github/workflows/backup-production-database.yml`  
**Script:** `scripts/backup_database.sh`

### One-time AWS setup

1. Create bucket (example name): `the-cookie-circle-db-backups`
   - Block all public access
   - Encryption: SSE-S3
   - Region: `ap-southeast-1` (or your preferred region)

2. S3 Lifecycle (recommended) on prefix `production/daily/`:
   - Expire objects after **30 days**

3. IAM user `cookie-circle-db-backup` with policy limited to:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::the-cookie-circle-db-backups",
        "arn:aws:s3:::the-cookie-circle-db-backups/production/*"
      ]
    }
  ]
}
```

Use a **dedicated** backup IAM user — not the same keys as `the-cookie-circle-assets-live`.

### GitHub secrets (`the-cookie-circle-api` repo)

| Secret | Value |
|--------|--------|
| `PRODUCTION_DATABASE_URL` | Neon production URL: `postgresql+psycopg://...?sslmode=require` |
| `S3_BACKUP_BUCKET` | `the-cookie-circle-db-backups` |
| `AWS_BACKUP_ACCESS_KEY_ID` | Backup IAM access key |
| `AWS_BACKUP_SECRET_ACCESS_KEY` | Backup IAM secret |
| `AWS_BACKUP_REGION` | `ap-southeast-1` |

### Verify

1. Push workflow to `main`
2. GitHub → **Actions** → **Backup production database** → **Run workflow**
3. Confirm object in S3: `production/daily/cookie_circle_production_*.dump`

Scheduled runs start automatically after the workflow is on `main`.

---

## Layer 3 — Manual backup before risky changes

**When:** Before every production migration or major deploy.

```bash
cd the-cookie-circle-api
export DATABASE_URL="postgresql+psycopg://..."   # production Neon URL
export AWS_ACCESS_KEY_ID="..."                  # backup IAM only
export AWS_SECRET_ACCESS_KEY="..."
export AWS_DEFAULT_REGION="ap-southeast-1"
export S3_BACKUP_BUCKET="the-cookie-circle-db-backups"

./scripts/backup_database.sh --prefix production/manual
```

Or trigger GitHub Actions manually with prefix `production/manual`.

Manual dumps can use a longer S3 lifecycle (e.g. expire after 90 days).

---

## Restore runbook (production)

### A — Full restore from S3 (disaster / bad migration)

1. **Stop writes:** pause Render API or enable maintenance if available.
2. **Download** latest dump from S3.
3. **Create** a new Neon branch or database (safer than overwriting in place).
4. **Restore:**

```bash
# URL must be plain postgresql:// for pg_restore
export TARGET_URL="postgresql://user:pass@host/neondb?sslmode=require"
pg_restore \
  --dbname="$TARGET_URL" \
  --no-owner \
  --no-acl \
  --clean \
  --if-exists \
  cookie_circle_production_YYYYMMDD_HHMMSS.dump
```

5. **Verify:** row counts, latest order, admin login.
6. **Check schema:** `uv run alembic current` (should match; run `upgrade head` only if behind).
7. **Point Render** `DATABASE_URL` at the restored database → redeploy API.
8. **Smoke test** checkout and admin.

### B — Recent oops (within Neon PITR window)

Use Neon **Restore** / branch from earlier time — faster than S3.

### C — Test on staging (recommended once)

Restore a daily dump to a throwaway Neon branch before you rely on production backups.

---

## Blockers?

| Requirement | Blocks backup? |
|-------------|----------------|
| Custom domain on Vercel | **No** |
| Client on `*.vercel.app` | **No** |
| Production Neon project + `DATABASE_URL` | **Yes** — must exist |
| S3 backup bucket + IAM | **Yes** — for Layer 2/3 uploads |
| GitHub secrets | **Yes** — for automated nightly job |
